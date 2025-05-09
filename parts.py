from machine import Pin, PWM
import asyncio
from servo import Servo
import time

class Aimer:
    def __init__(self, vservo, hservo):
        self.vservo = vservo
        self.hservo = hservo

        self.vgain = -4
        self.hgain = -4
        self.vspeed = 50
        self.hspeed = 50

        self.vlim_min = -25
        self.vlim_max = 35

        self.hlim_min = -15
        self.hlim_max = 15


    def aim(self, vangle, hangle):
        vangle = min(max(self.vlim_min, vangle), self.vlim_max)
        hangle = min(max(self.hlim_min, hangle), self.hlim_max)

        print(f"Aimer: Aiming to {vangle}V {hangle}H")

        self.vservo.move(180 + vangle*self.vgain, self.vspeed)
        self.hservo.move(180 + hangle*self.hgain, self.hspeed)

    def status(self):
        try:
            vangle_raw = self.vservo.status()["angle"]
            hangle_raw = self.hservo.status()["angle"]
        except:
            return dict(
                tilt=0,
                pan=0,
            )

        return dict(
            tilt=(vangle_raw - 180)/self.vgain,
            pan=(hangle_raw - 180)/self.hgain,
        )

    def calibrate(self):
        self.vservo.calibrate_middle()
        self.hservo.calibrate_middle()
        return True

class Feeder:
    """Uses a st servo in wheel mode to feed balls into the launcher"""
    def __init__(self, st_servo, shaker: None):
        self.st_servo = st_servo
        self.shaker = shaker
        self.active = False
        self.interval = 4
        self.deg_ball = 60 # new ball every 60deg
        self.wait = 0.25

    def set_ball_interval(self, seconds):
        self.interval = max(0.5, seconds)
        print(f"Feeder: Ball interval set to {self.interval}s")

    async def feed_one(self):
        print("not implemented")

    async def run(self):
        while True:
            await asyncio.sleep(self.wait)
            if self.active:
                speed = self.deg_ball / self.interval
                self.st_servo.move(0, speed)
            else:
                try:
                    self.st_servo.move(0, 0)
                except:
                    pass

    def activate(self):
        print("Feeder: Activate")
        self.active = True
        if self.shaker:
            self.shaker.active = True

    def halt(self):
        print("Feeder: Halt")
        self.active = False
        if self.shaker:
            self.shaker.active = False

    def status(self):
        return dict(active=self.active, interval=self.interval)


class Shaker:
    """Uses a servo to stir balls"""
    def __init__(self, servo_pin: int):
        self._pin_no = servo_pin
        self.servo = Servo(servo_pin)
        self.stop_ns = 1570000
        self.servo.__motor.duty_ns(self.stop_ns)
        self.move_us = 0
        self.active = False


    async def run(self):
        while True:
            await asyncio.sleep(1)
            if self.active:
                self.servo.__motor.duty_ns(int(self.stop_ns + self.move_us * 1e3))
            else:
                self.servo.__motor.duty_ns(self.stop_ns)



class ESC:
    def __init__(self, pin, name, freq=50):
        self.pin = Pin(pin, Pin.OUT)
        self.name = name
        self.pwm = PWM(self.pin, freq=freq)
        self.min_pulse = 1000000  # ns
        self.max_pulse = 2000000  # ns
        self.speed = 0
        self._current_pulse = 0
        self.limit = 100
        self.set_speed(0)

    def calibrate_1(self):
        """Must be called before the ESC is powered up"""
        self.pwm.duty_ns(self.max_pulse)

    def calibrate_2(self):
        """Must be called after the ESC has powered up and entered programming mode"""
        self.pwm.duty_ns(self.min_pulse)

    def set_speed(self, speed_pc, force=False):
        if speed_pc > self.limit:
            print(f"Capping speed to limit {self.limit}")
            speed_pc = self.limit
        if speed_pc <= 0:
            speed_pc = 0

        pulse = int(speed_pc / 100 * (self.max_pulse - self.min_pulse) + self.min_pulse)
        self.speed = speed_pc
        self._current_pulse = pulse

        if force:
            self.pwm.duty_ns(pulse)
            self.spin_up()

    def spin_up(self):
        self.pwm.duty_ns(self._current_pulse)

    def status(self):
        return f"{self.name}{self.speed:2.0f}"

class Launcher:
    """Shoots balls using 3 brushless motors"""

    def __init__(self, top, left, right):
        self._esc = {
            "top": ESC(top, name="T"),
            "left": ESC(left, "L"),
            "right": ESC(right, "R"),
        }

        self._cos30 = 0.866
        self._sin30 = 0.5

        self.raw_minimum = 5
        self.raw_maximum = 9
        self.raw_spin = 3 * 2 * self._cos30 * self.raw_minimum / 5 # should ensure does not go negative ever
        self.active = False
        self.speed = 0
        self.topspin = 0
        self.sidespin = 0
        self.left_speed = 0
        self.right_speed = 0
        self.top_speed = 0

    def set_speed(self, motor, percentage, force=False):
        assert 0 <= percentage <= 100

        assert motor in ["all", "top", "left", "right"]

        if motor == "all":
            for motor_name, motor_esc in self._esc.items():
                motor_esc.set_speed(percentage, force)

        else:
            self._esc[motor].set_speed(percentage, force)

    def activate(self):
        """Accelerate towards launching speed"""
        for motor in self._esc.values():
            motor.spin_up()
        self.active = True

    def halt(self):
        """Turn off"""
        for motor in self._esc.values():
            motor.set_speed(0, force=True)
        self.active = False

    def configure(self, speed, topspin, sidespin):
        assert 0 <= speed <= 100
        assert -1 <= topspin <= 1
        assert -1 <= sidespin <= 1

        # base speed is the given setting
        if speed == 0:
            base_speed = 0
        else:
            base_speed = (self.raw_maximum - self.raw_minimum) * speed / 100 + self.raw_minimum

        top = topspin * self.raw_spin
        side = sidespin * self.raw_spin

        left_speed = (3 * base_speed - top - 3/2 * side / self._cos30) / 3
        right_speed = left_speed + side / self._cos30
        top_speed = top + self._sin30 * (left_speed + right_speed)

        if left_speed < self.raw_minimum:
            print("Warning: settings make left speed stall")
        if right_speed < self.raw_minimum:
            print("Warning: settings make right speed stall")
        if top_speed < self.raw_minimum:
            print("Warning: settings make top speed stall")

        left_speed = max(left_speed, 0)
        right_speed = max(right_speed, 0)
        top_speed = max(top_speed, 0)

        print(f"Requested speed {base_speed}, (T+L+R)/3 = {(top_speed + right_speed + left_speed) / 3}")

        print(f"Configuring for speed {speed}, top {topspin}, side {sidespin}")
        print(f"Top {top_speed:.1f}, Left {left_speed:.1f}, Right {right_speed:.1f}")

        self.speed = speed
        self.topspin = topspin
        self.sidespin = sidespin
        self.top_speed = top_speed
        self.right_speed = right_speed
        self.left_speed = left_speed

        self._esc["top"].set_speed(top_speed)
        self._esc["left"].set_speed(left_speed)
        self._esc["right"].set_speed(right_speed)

    def status(self):
        return dict(
            active=self.active,
            speed=self.speed,
            top_speed=self.top_speed,
            right_speed=self.right_speed,
            left_speed=self.left_speed,
            topspin=self.topspin,
            sidespin=self.sidespin,
        )
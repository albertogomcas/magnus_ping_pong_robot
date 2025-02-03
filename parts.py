from machine import Pin, PWM
import asyncio
from servo import Servo

class Aimer:
    def __init__(self, vaxis:str, haxis:str):
        self.vaxis = vaxis
        self.haxis = haxis
        self.vservo = Servo(vaxis)
        self.hservo = Servo(haxis)
        self.voffset = 10
        self.hoffset = 10
        self.vlim_min = 0
        self.vlim_max = 45
        self.hlim_min = 0
        self.hlim_max = 20
        self.vaim = 0
        self.haim = 0
        self.aim(0,0)

    def aim(self, vangle, hangle):
        if vangle is not None:
            vangle = min(max(self.vlim_min, vangle + self.voffset), self.vlim_max)
            self.vaim = vangle

        if hangle is not None:
            hangle = min(max(self.hlim_min, hangle + self.hoffset), self.hlim_max)
            self.haim = hangle

        print(f"Aiming {self.vaim}V {self.haim}H")

        self.vservo.move(self.vaim)
        self.hservo.move(self.haim)

    def status(self):
        return dict(
            tilt=self.vaim-self.voffset,
            pan=self.haim-self.hoffset,
        )


class Feeder:
    """Uses a stepper to feed balls into the launcher"""
    def __init__(self, servo_pin: int):
        self._pin_no = servo_pin
        self.servo = Servo(servo_pin)
        self.active = False
        self.interval = 4
        self.step = 60
        self.wait = 0.25

    def set_ball_interval(self, seconds):
        self.interval = max(0.5, seconds)
        print(f"Ball interval: {self.interval}s")

    async def feed_one(self):
        self.servo.move(0)
        await asyncio.sleep(self.wait)
        self.servo.move(self.step)
        await asyncio.sleep(self.wait)
        self.servo.move(0)
        await asyncio.sleep(self.wait)


    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            if self.active:
                print("push ball")
                await self.feed_one()

    def activate(self):
        self.active = True

    def halt(self):
        self.active = False

    def status(self):
        return dict(active=self.active, interval=self.interval)

class ESC:
    def __init__(self, pin, name, freq=50):
        self.pin = Pin(pin, Pin.OUT)
        self.name = name
        self.pwm = PWM(self.pin, freq=freq)
        self.min_pulse = 1000000  # ns
        self.max_pulse = 2000000  # ns
        self.speed = 0
        self._current_pulse = 0
        self._idle_factor = 0.5
        self._idling = False
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

    def idle_down(self):
        self.pwm.duty_ns(int(self._current_pulse * self._idle_factor))
        self._idling = True

    def spin_up(self):
        self.pwm.duty_ns(self._current_pulse)
        self._idling = False

    def status(self):
        idling = " " if not self._idling else "I"
        return f"{self.name}{self.speed:2.0f}{idling}"

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
        self.raw_maximum = 8
        self.raw_spin = 5
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
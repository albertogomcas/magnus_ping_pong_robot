import time
from machine import Pin, PWM
import asyncio

import arduino
from arduino import arduino_uart

class Aimer:
    def __init__(self, vaxis:str, haxis:str):
        self.vaxis = vaxis
        self.haxis = haxis
        self._steps_rev = 200 * 14 # geared
        self.vlim_min = -10
        self.vlim_max = 10
        self.hlim_min = -10
        self.hlim_max = 10

    def aim(self, vangle, hangle):

        vangle = min(max(self.vlim_min, vangle), self.vlim_max)
        hangle = min(max(self.hlim_min, hangle), self.hlim_max)
        print(f"Aiming {vangle}V {hangle}H")

        vsteps = int(vangle / 360 * self._steps_rev)
        hsteps = int(hangle / 360 * self._steps_rev)

        arduino_uart.write(b"\r\n\r\n")
        time.sleep(0.1)
        arduino_uart.flush()
        if self.vaxis:
            arduino_uart.write(f"<mvto {self.vaxis} {vsteps}>\r\n".encode("ascii"))
            time.sleep(0.1)
        if self.haxis:
            arduino_uart.write(f"<mvto {self.haxis} {hsteps}>\r\n".encode("ascii"))
            time.sleep(0.1)
        pending = arduino_uart.any()
        if pending:
            print(arduino_uart.read(pending))

class Feeder:
    """Uses a stepper to feed balls into the launcher"""
    def __init__(self, axis:str, shaker_pin:int):
        self.axis = axis
        self.active = False
        self.interval = 4
        self._steps_rev = 200 * 14 * 2 # geared
        self.step = - self._steps_rev / 5
        self.shaker = PWM(Pin(shaker_pin, Pin.OUT))
        self.shaker.freq(50)
        self.shaker.duty_ns(int(1.5e6))

    def set_ball_interval(self, seconds):
        self.interval = max(0.5, seconds)
        print(f"Ball interval: {self.interval}s")

    async def feed_one(self):
        arduino_uart.write(b"\r\n\r\n")
        time.sleep(0.1)
        arduino_uart.flush()
        arduino_uart.write(f"<mvby {self.axis} {self.step}>\r\n".encode("ascii"))
        await asyncio.sleep(0.1)
        pending = arduino_uart.any()
        if pending:
            print(arduino_uart.read(pending))


    async def run(self):
        while True:
            await asyncio.sleep(self.interval)
            if self.active:
                self.shaker.duty_ns(int(1.58e6))
                print("push ball")
                arduino_uart.write(b"\r\n\r\n")
                time.sleep(0.1)
                arduino_uart.flush()
                arduino_uart.write(f"<mvby {self.axis} {self.step}>".encode("ascii"))
                await asyncio.sleep(0.1)
                pending = arduino_uart.any()
                if pending:
                    print(arduino_uart.read(pending))

    def activate(self):
        self.active = True

    def halt(self):
        self.active = False
        arduino_uart.write(f"<stop {self.axis}>\r\n")
        self.shaker.duty_ns(int(1.5e6))



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
        """Must be called after the ESC has powered up and etered programming mode"""
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

    def __init__(self, bottom, left, right):
        self._esc = {
            "bottom": ESC(bottom, name="B"),
            "left": ESC(left, "L"),
            "right": ESC(right, "R"),
        }

        self.raw_minimum = 5
        self.raw_maximum = 8
        self.raw_spin_factor = 10
        self.raw_spin = (self.raw_maximum - self.raw_minimum) / self.raw_spin_factor


    def set_speed(self, motor, percentage, force=False):
        assert 0 <= percentage <= 100

        assert motor in ["all", "bottom", "left", "right"]

        if motor == "all":
            for motor_name, motor_esc in self._esc.items():
                motor_esc.set_speed(percentage, force)

        else:
            self._esc[motor].set_speed(percentage, force)

    def activate(self):
        """Accelerate towards launching speed"""
        for motor in self._esc.values():
            motor.spin_up()

    def halt(self):
        """Turn off"""
        for motor in self._esc.values():
            motor.set_speed(0, force=True)

    def configure(self, speed, topspin, sidespin):
        assert 0 <= speed <= 100
        assert -1 <= topspin <= 1
        assert -1 <= sidespin <= 1

        # base speed is the given setting
        if speed == 0:
            base_speed = 0
        else:
            base_speed = (self.raw_maximum - self.raw_minimum) * speed / 100 + self.raw_minimum

        # a differential top/bottom speed is calculated based on the spin
        top_bottom_diff = self.raw_spin * topspin
        side_speed_diff = sidespin * base_speed

        left_speed = base_speed + side_speed_diff + top_bottom_diff / 2
        right_speed = base_speed - side_speed_diff + top_bottom_diff / 2
        bottom_speed = base_speed - top_bottom_diff
        # a differential left/right speed is calculated based on side spin


        print(f"Configuring for speed {speed}, top {topspin}, side {sidespin}")
        print(f"Bottom {bottom_speed:.1f}, Left {left_speed:.1f}, Right {right_speed:.1f}")

        self._esc["bottom"].set_speed(bottom_speed)
        self._esc["left"].set_speed(left_speed)
        self._esc["right"].set_speed(right_speed)

    def status(self):
        status = ""
        order = ["left", "bottom", "right"]
        for mname in order:
            status += f"{self._esc[mname].status()} "

        return status
from machine import Pin, PWM

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

        pulse = int(speed_pc/100 * (self.max_pulse - self.min_pulse) + self.min_pulse)
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

    def ease(self):
        """Decelerate towards idle speed"""
        for motor in self._esc.values():
            motor.idle_down()

    def halt(self):
        """Turn off"""
        for motor in self._esc.values():
            motor.set_speed(0, force=True)

    def configure(self, speed, topspin, sidespin):
        assert 0 <= speed <= 100
        assert -1 <= topspin <= 1
        assert -1 <= sidespin <= 1

        # base speed is the given setting
        base_speed = speed
        # a differential top/bottom speed is calculated based on the spin
        bottom_speed = base_speed * (1 - topspin/2) # half speed when topspin is maximum
        left_top_speed = base_speed * (1 + topspin/2)
        right_top_speed = base_speed * (1 + topspin/2)

        # a differential left/right speed is calculated based on side spin
        side_speed_diff = 0.5 * left_top_speed * sidespin

        left_speed = max(0, left_top_speed - side_speed_diff)
        right_speed = max(0, right_top_speed + side_speed_diff)

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


if __name__ == "__main__":
    launcher = Launcher(1, 2, 3)

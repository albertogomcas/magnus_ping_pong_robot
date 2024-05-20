from machine import Pin, PWM
class Feeder:
    """Uses a 360 servo to feed balls into the launcher"""
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
        self.pwm = PWM(self.pin, freq=50)

    def activate(self):
        self.pwm.duty_ns(1500000-500000)
        #self.pwm.duty_ns(1500000 - 1000)

    def halt(self):
        self.pwm.duty_ns(1500000)
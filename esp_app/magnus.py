from microdot import Microdot, Response
import machine
from machine import Pin, UART

import dev
from ujrpc import JRPCService
import time
from parts import Feeder, Launcher, Aimer, Shaker, Detector, Supply
import asyncio
import math
from stservo_wrapper import STServo
from stservo.port_handler import PortHandlerMicroPython


class UsedPins:
    PROGRAM = 19  # pullup
    ESC_ALIVE = 36# adc sv
    LAUNCHER_LEFT = 32
    DETECTOR = 34
    LAUNCHER_TOP = 25
    LAUNCHER_RIGHT = 33
    SHAKER_SERVO = 21
    ST_SERVO_TX = 23
    ST_SERVO_RX = 22

    @classmethod
    def sanity_check(cls):
        all_numbers = []
        for key, value in cls.__dict__.items():
            if not key.startswith("__"):
                if value in all_numbers:
                    print(f"{key} Pin {value} already in use")
                    raise ValueError(f"{key} Pin {value} already in use")
                else:
                    all_numbers.append(value)

class Magnus:
    def __init__(self):
        self.supply = Supply(UsedPins.ESC_ALIVE)
        self.ST_UART = UART(1, baudrate=1000000, tx=Pin(UsedPins.ST_SERVO_TX), rx=Pin(UsedPins.ST_SERVO_RX))
        self.port_handler = PortHandlerMicroPython(self.ST_UART)
        self.feeder_servo = STServo(self.port_handler, servo_id=9)
        self.shaker = Shaker(UsedPins.SHAKER_SERVO)

        self.feeder = Feeder(self.feeder_servo, shaker=self.shaker)

        self.launcher = Launcher(UsedPins.LAUNCHER_TOP, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT)
        self.launcher.halt()
        self.detector = Detector(UsedPins.DETECTOR)
        self.vertical_servo = STServo(self.port_handler, servo_id=3)
        self.horizontal_servo = STServo(self.port_handler, servo_id=6)
        self.aimer = Aimer(self.vertical_servo, self.horizontal_servo)

    def calibrate(self):
        self.launcher.set_speed("all", 100, force=True)
        time.sleep(3)
        self.launcher.halt()
        self.launcher.set_speed("all", 0)
        print("Calibrated")
        time.sleep(1)

    async def activate(self):
        self.launcher.activate()
        self.feeder.activate()

    async def halt(self):
        self.launcher.halt()
        self.feeder.halt()

    def status(self):
        status = {
            "supply": self.supply.status(),
            "launcher": self.launcher.status(),
            "feeder": self.feeder.status(),
            "aim": self.aimer.status(),
            "detector": self.detector.status(),
        }
        return status

    def set_settings(self, **settings):
        interval = settings.get("feed_interval", None)
        if interval is not None:
            self.feeder.set_ball_interval(interval)

        self.aimer.aim(
            vangle=settings.get("tilt", None),
            hangle=settings.get("pan", None),
        )

        speed = settings["speed"]
        spin_angle = settings["spin_angle"]
        spin_strength = settings["spin_strength"]

        topspin = math.cos(math.radians(spin_angle)) * spin_strength / 100
        sidespin = math.sin(math.radians(spin_angle)) * spin_strength / 100

        self.launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)

        shaker_tuning_f = settings["shaker_f"]
        shaker_tuning_r = settings["shaker_r"]
        if shaker_tuning_f is not None:
            self.shaker.move_us = shaker_tuning_f
        if shaker_tuning_r is not None:
            self.shaker.reverse_move_us = shaker_tuning_r

        if settings["launcher_active"]:
            self.launcher.activate()
        else:
            self.feeder.halt()
            self.launcher.halt()

        if settings["feeder_active"]:
            if self.launcher.active and self.launcher.speed > 0:
                self.feeder.activate()
        else:
            print("Launcher is not running, feeder activation prevented")
            self.feeder.halt()

    def feed_one(self):
        if self.launcher.active:
            print("Feeding one")
            self.feeder.feed_one()
        else:
            print("Launcher not active, not feeding")
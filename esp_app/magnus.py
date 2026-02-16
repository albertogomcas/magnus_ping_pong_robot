from microdot import Microdot, Response
from machine import Pin, UART
import time

import dev
from parts import Feeder, Launcher, Aimer, Shaker, Detector, Supply, Remote, ESPNowRemote
import asyncio
import math
from stservo_wrapper import STServo
from stservo.port_handler import PortHandlerMicroPython
import random


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
    # REMOTE_RX = 27  # No longer needed for ESP-NOW remote

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

class ServoNumbers:
    feeder = 9
    shaker = 10
    launcher_v = 3
    launcher_h = 6

class Magnus:
    def __init__(self):
        self.supply = Supply(UsedPins.ESC_ALIVE)
        self.ST_UART = UART(1, baudrate=1000000, tx=Pin(UsedPins.ST_SERVO_TX), rx=Pin(UsedPins.ST_SERVO_RX))
        self.port_handler = PortHandlerMicroPython(self.ST_UART)

        self.feeder_servo = STServo(self.port_handler, servo_id=ServoNumbers.feeder)
        self.vertical_servo = STServo(self.port_handler, servo_id=ServoNumbers.launcher_v)
        self.horizontal_servo = STServo(self.port_handler, servo_id=ServoNumbers.launcher_h)
        self.shaker_servo = STServo(self.port_handler, servo_id=ServoNumbers.shaker)

        self.shaker = Shaker(self.shaker_servo)
        self.feeder = Feeder(self.feeder_servo, shaker=self.shaker)

        self.launcher = Launcher(UsedPins.LAUNCHER_TOP, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT, feeder=self.feeder)
        self.launcher.halt()
        self.detector = Detector(UsedPins.DETECTOR)

        self.aimer = Aimer(self.vertical_servo, self.horizontal_servo)
        self.sequence = []
        self.active_sequence = False
        self._randomize_sequence = False
        self._sequence_idx = 0
        self._sequence_task = None

        # Initialize ESP-NOW remote (auto-detects WiFi channel)
        # Status sending now enabled - fixed to add peers with channel parameter
        self.remote = ESPNowRemote(enable_status_send=True)

        # Bind actions to remote commands
        # Layer 0 - Control
        self.remote.bind("aimer_up", self.aimer.up)
        self.remote.bind("aimer_down", self.aimer.down)
        self.remote.bind("aimer_center", self.aimer.middle)
        self.remote.bind("aimer_left", self.aimer.left)
        self.remote.bind("aimer_right", self.aimer.right)
        self.remote.bind("toggle_activation", self.toggle_activation)
        self.remote.bind("feed_one", self.feed_one)

        # Layer 1 - Spin presets
        self.remote.bind("spin_TL", self.launcher.spin_TL)
        self.remote.bind("spin_T", self.launcher.spin_T)
        self.remote.bind("spin_TR", self.launcher.spin_TR)
        self.remote.bind("spin_L", self.launcher.spin_L)
        self.remote.bind("spin_R", self.launcher.spin_R)
        self.remote.bind("spin_BL", self.launcher.spin_BL)
        self.remote.bind("spin_B", self.launcher.spin_B)
        self.remote.bind("spin_BR", self.launcher.spin_BR)
        self.remote.bind("spin_random", self.launcher.spin_random)
        self.remote.bind("no_spin", self.launcher.no_spin)

        # Layer 2 - Settings
        self.remote.bind("speed_up", self.launcher.speed_up)
        self.remote.bind("speed_down", self.launcher.speed_down)
        self.remote.bind("increase_spin", self.launcher.increase_spin)
        self.remote.bind("decrease_spin", self.launcher.decrease_spin)
        self.remote.bind("interval_up", self.interval_up)
        self.remote.bind("interval_down", self.interval_down)

        # Set status callback for broadcasting to remote
        # Use remote_status() which returns a flat structure suitable for OLED display
        self.remote.set_status_callback(self.remote_status)




    def calibrate(self):
        self.launcher.set_speed("all", 100, force=True)
        time.sleep(3)
        self.launcher.halt()
        self.launcher.set_speed("all", 0)
        print("[Magnus] calibrated")
        time.sleep(1)

    def interval_up(self):
        """Increase feed interval"""
        current = self.feeder.interval
        new_interval = min(current + 0.5, 10)
        self.feeder.set_ball_interval(new_interval)
        print(f"[Magnus] Interval increased to {new_interval}s")

    def interval_down(self):
        """Decrease feed interval"""
        current = self.feeder.interval
        new_interval = max(current - 0.5, 0.5)
        self.feeder.set_ball_interval(new_interval)
        print(f"[Magnus] Interval decreased to {new_interval}s")

    def toggle_activation(self):
        # If speed is 0, set a default speed before activating
        if self.launcher.speed == 0:
            print("[Magnus] Speed is 0, setting default speed to 50")
            self.launcher.configure(speed=50, topspin=0, sidespin=0, activate=False)

        if self.launcher.active and self.feeder.active:
            print("[Magnus] deactivating launcher and feeder")
            self.launcher.halt()
        elif self.launcher.active and not self.feeder.active:
            if self.launcher.speed > 0:
                print("[Magnus] activating feeder")
                self.feeder.activate()
        elif (not self.launcher.active) and (not self.feeder.active) and self.launcher.speed > 0:
            print("[Magnus] activating launcher and feeder")
            self.launcher.activate()
            self.feeder.activate()
        else:
            print("[Magnus] stop launcher and feeder")
            self.launcher.halt()

    async def activate(self):
        self.launcher.activate()
        self.feeder.activate()

    async def halt(self):
        self.launcher.halt()

    def status(self):
        status = {
            "supply": self.supply.status(),
            "launcher": self.launcher.status(),
            "feeder": self.feeder.status(),
            "aim": self.aimer.status(),
            "detector": self.detector.status(),
            "sequence": self.active_sequence,
        }
        return status

    def remote_status(self):
        """Return flattened status for remote OLED display"""
        launcher = self.launcher.status()
        aim = self.aimer.status()
        feeder = self.feeder.status()

        return {
            'launcher_active': launcher['active'],
            'speed': int(launcher['speed']),
            'topspin': launcher['topspin'],
            'sidespin': launcher['sidespin'],
            'spin_angle': int(launcher['spin_angle']),
            'spin_strength': int(launcher['spin_strength']),
            'tilt': aim['tilt'],
            'pan': aim['pan'],
            'interval': feeder['interval'],
        }

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

        if settings.get("launcher_active", False):
            self.launcher.activate()
        else:
            self.launcher.halt()

        if settings.get("feeder_active", False):
            if self.launcher.active and self.launcher.speed > 0:
                self.feeder.activate()
        else:
            print("[Magnus] launcher is not running, feeder activation prevented")
            self.feeder.halt()

    def feed_one(self):
        if self.launcher.active:
            print("[Magnus] feeding one")
            self.feeder.feed_one()
        else:
            print("[Magnus] launcher not active, not feeding")

    def set_sequence(self, sequence):
        self.sequence = sequence
        self.active_sequence = False

    def start_sequence(self, randomize_order=False, feed_interval=1):
        self._randomize_sequence = randomize_order
        self.feeder.set_ball_interval(feed_interval)
        self.active_sequence = True
        self._sequence_task = asyncio.create_task(self.run_sequence())

    def stop_sequence(self):
        self.active_sequence = False

    async def run_sequence(self):
        while self.active_sequence:
            print(f"[Magnus] running sequence step {self._sequence_idx + 1}/{len(self.sequence)}")
            self.set_settings(**self.sequence[self._sequence_idx], launcher_active=True, feeder_active=True)
            await asyncio.sleep(0.5)
            await self.wait_detector()
            if not self._randomize_sequence:
                self._sequence_idx += 1
                if self._sequence_idx >= len(self.sequence):
                    self._sequence_idx = 0
            else:
                self._sequence_idx = random.randint(0, len(self.sequence) - 1)

    async def wait_detector(self):
        start = time.time()
        while time.time() - start < 30:
            await asyncio.sleep_ms(100)
            if self.detector.status()["elapsed"] < 0.2:
                print("[Magnus] Detected ball, continuing sequence")
                break

        else: # no break
            print("[Magnus] detector did not finish within 30 seconds, stopping sequence")
            self.stop_sequence()
            self.halt()
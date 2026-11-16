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
try:
    from .drill_store import DrillStore
except ImportError:
    from drill_store import DrillStore

# Pre-allocated UART instance - set by boot.py before heap gets fragmented
_preallocated_uart = None


def _remote_text(value, limit):
    return "".join(
        char if 32 <= ord(char) <= 126 and char not in '"\\' else "?"
        for char in str(value)[:limit]
    )


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
        import gc
        global _preallocated_uart
        gc.collect()
        print(f"[Magnus] Free memory at init: {gc.mem_free()} bytes")

        # Reuse UART pre-allocated in boot.py (before heap fragmentation)
        if _preallocated_uart is not None:
            self.ST_UART = _preallocated_uart
            _preallocated_uart = None  # release the module-level reference
            print("[Magnus] Reusing pre-allocated UART")
        else:
            self.ST_UART = UART(1, baudrate=1000000, tx=Pin(UsedPins.ST_SERVO_TX), rx=Pin(UsedPins.ST_SERVO_RX), rxbuf=512, txbuf=256)
            print("[Magnus] Created new UART (no pre-allocation found)")
        self.supply = Supply(UsedPins.ESC_ALIVE)
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
        self._loop_sequence = True
        self._sequence_idx = 0
        self._sequence_order = []
        self._sequence_generation = 0
        self._sequence_task = None
        self._watchdog_task = None
        self.drill_store = DrillStore()
        self.sequence_draft = []
        self.remote_message = ""

        # Remote will be initialized after WiFi connects
        self.remote = None




    def enable_remote(self):
        """Initialize ESP-NOW remote after WiFi is connected (so the channel is known)."""
        self.remote = ESPNowRemote(enable_status_send=True)

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

        for slot in range(1, 10):
            slot_text = str(slot)
            self.remote.bind(
                "apply_preset_" + slot_text,
                lambda slot=slot_text: self.apply_preset(slot),
            )
            self.remote.bind(
                "save_preset_" + slot_text,
                lambda slot=slot_text: self.save_preset(slot),
            )
            self.remote.bind(
                "append_preset_" + slot_text,
                lambda slot=slot_text: self.append_preset(slot),
            )
            self.remote.bind(
                "save_sequence_" + slot_text,
                lambda slot=slot_text: self.save_sequence(slot),
            )
            self.remote.bind(
                "start_sequence_" + slot_text,
                lambda slot=slot_text: self.start_saved_sequence(slot),
            )
            self.remote.bind(
                "start_random_sequence_" + slot_text,
                lambda slot=slot_text: self.start_saved_sequence(slot, randomize_order=True),
            )
        self.remote.bind("remove_sequence_step", self.remove_sequence_step)
        self.remote.bind("clear_sequence_draft", self.clear_sequence_draft)
        self.remote.bind("toggle_sequence_loop", self.toggle_sequence_loop)
        self.remote.bind("stop_sequence", self.stop_sequence)

        self.remote.set_status_callback(self.remote_status)
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self.servo_watchdog())
        print("[Magnus] Remote enabled")

    def calibrate(self):
        self.launcher.set_speed("all", 100, force=True)
        time.sleep(3)
        self.launcher.halt()
        self.launcher.set_speed("all", 0)
        print("[Magnus] calibrated")
        time.sleep(1)

    def interval_up(self, step=0.25):
        """Increase feed interval
        step: Interval increase in seconds (default 0.25, larger for long press)
        """
        current = self.feeder.interval
        new_interval = min(current + step, 10)
        self.feeder.set_ball_interval(new_interval)
        print(f"[Magnus] Interval increased by {step}s to {new_interval}s")

    def interval_down(self, step=0.25):
        """Decrease feed interval
        step: Interval decrease in seconds (default 0.25, larger for long press)
        """
        current = self.feeder.interval
        new_interval = max(current - step, 0.5)
        self.feeder.set_ball_interval(new_interval)
        print(f"[Magnus] Interval decreased by {step}s to {new_interval}s")

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
            "servo_comm_failures": {
                name: servo.comm_failures
                for name, servo in (
                    ("feeder", self.feeder_servo),
                    ("shaker", self.shaker_servo),
                    ("vertical", self.vertical_servo),
                    ("horizontal", self.horizontal_servo),
                )
            },
        }
        return status

    def remote_status(self):
        """Return flattened status for remote OLED display"""
        launcher = self.launcher.status()
        try:
            aim = self.aimer.status()
            aim_error = ""
        except RuntimeError as exc:
            aim = {"tilt": None, "pan": None}
            aim_error = str(exc)
        feeder = self.feeder.status()

        return {
            'a': launcher['active'],
            's': int(launcher['speed']),
            'sa': int(launcher['spin_angle']),
            'ss': int(launcher['spin_strength']),
            't': round(aim['tilt'], 1) if aim['tilt'] is not None else None,
            'p': round(aim['pan'], 1) if aim['pan'] is not None else None,
            'i': round(feeder['interval'], 2),
            'q': self.active_sequence,
            'd': len(self.sequence_draft),
            'l': self._loop_sequence,
            'm': _remote_text(self.remote_message, 16),
            'e': _remote_text((self.remote.last_error if self.remote else "") or aim_error, 48),
            'n': self.remote.error_id if self.remote else 0,
        }

    def set_settings(self, **settings):
        # Read current state for fallback values
        launcher_st = self.launcher.status()
        aim_st = self.aimer.status()
        feeder_st = self.feeder.status()

        interval = settings.get("feed_interval", None)
        if interval is not None:
            self.feeder.set_ball_interval(interval)

        tilt = settings.get("tilt", aim_st["tilt"])
        pan = settings.get("pan", aim_st["pan"])
        self.aimer.aim(vangle=tilt, hangle=pan)

        speed = settings.get("speed", launcher_st["speed"])
        spin_angle = settings.get("spin_angle", launcher_st["spin_angle"])
        spin_strength = settings.get("spin_strength", launcher_st["spin_strength"])

        topspin = math.cos(math.radians(spin_angle)) * spin_strength / 100
        sidespin = math.sin(math.radians(spin_angle)) * spin_strength / 100

        self.launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)

        launcher_active = settings.get("launcher_active", launcher_st["active"])
        feeder_active = settings.get("feeder_active", feeder_st["active"])

        if launcher_active:
            self.launcher.activate()
        else:
            self.launcher.halt()

        if feeder_active:
            if self.launcher.active and self.launcher.speed > 0:
                self.feeder.activate()
        else:
            print("[Magnus] feeder deactivated")
            self.feeder.halt()

    def feed_one(self):
        if self.launcher.active:
            print("[Magnus] feeding one")
            self.feeder.feed_one()
        else:
            print("[Magnus] launcher not active, not feeding")

    def flush_servo_uart(self):
        """Discard any stale bytes sitting in the UART RX buffer."""
        stale = self.ST_UART.any()
        if stale > 0:
            print(f"[Magnus] Flushing {stale} stale UART bytes")
            self.ST_UART.read(stale)

    async def servo_watchdog(self):
        """Periodically flush the UART and ping a servo to detect bus lock-ups."""
        print("[Magnus] Servo watchdog started")
        while True:
            await asyncio.sleep(10)
            if dev.DevFlags.simulation_mode:
                continue
            try:
                self.flush_servo_uart()
                pos, spd, comm, err = self.feeder_servo.sts.ReadPosSpeed(self.feeder_servo.servo_id)
                from stservo.stservo_def import COMM_SUCCESS
                if comm != COMM_SUCCESS:
                    print(f"[Magnus] Watchdog: servo ping failed ({comm}), flushing UART")
                    self.flush_servo_uart()
            except Exception as e:
                print(f"[Magnus] Watchdog error: {e}, flushing UART")
                self.flush_servo_uart()


    def set_sequence(self, sequence):
        if not isinstance(sequence, list) or not sequence:
            raise ValueError("A drill sequence must contain at least one preset")
        if self.active_sequence:
            self.stop_sequence()
        self.sequence = sequence
        self._sequence_order = list(range(len(sequence)))
        self._sequence_idx = 0

    def start_sequence(self, randomize_order=False, feed_interval=1, loop=True):
        if not self.sequence:
            raise ValueError("Cannot start a drill with an empty sequence")
        if self._sequence_task is not None:
            raise RuntimeError("A drill sequence is already running or stopping")
        self._randomize_sequence = randomize_order
        self._loop_sequence = loop
        self._sequence_order = list(range(len(self.sequence)))
        if self._randomize_sequence:
            random.shuffle(self._sequence_order)
        self._sequence_idx = 0
        self.feeder.set_ball_interval(feed_interval)
        if self._watchdog_task is None:
            self._watchdog_task = asyncio.create_task(self.servo_watchdog())
        self._sequence_generation += 1
        generation = self._sequence_generation
        self._sequence_task = asyncio.create_task(self.run_sequence(generation))
        self.active_sequence = True

    def stop_sequence(self):
        self.active_sequence = False
        self._sequence_generation += 1
        task = self._sequence_task
        self._sequence_task = None
        if task is not None:
            task.cancel()
        self.launcher.halt()
        self.feeder.halt()

    async def run_sequence(self, generation):
        try:
            while self.active_sequence and generation == self._sequence_generation:
                print(f"[Magnus] running sequence step {self._sequence_idx + 1}/{len(self.sequence)}")
                preset_index = self._sequence_order[self._sequence_idx]
                step_settings = {
                    key: value
                    for key, value in self.sequence[preset_index].items()
                    if key != "feed_interval"
                }
                detector_count = self.detector.status()["count"]
                self.set_settings(**step_settings, launcher_active=True, feeder_active=True)
                step_started = time.ticks_ms()
                await asyncio.sleep(0.5)
                if not self.active_sequence or generation != self._sequence_generation:
                    break
                self.flush_servo_uart()
                if not await self.wait_detector(generation, detector_count, step_started):
                    break
                self._sequence_idx += 1
                if self._sequence_idx >= len(self._sequence_order):
                    if self._loop_sequence:
                        self._sequence_idx = 0
                        if self._randomize_sequence:
                            random.shuffle(self._sequence_order)
                    else:
                        break
        finally:
            if generation == self._sequence_generation:
                self.active_sequence = False
                self.launcher.halt()
                self.feeder.halt()
                self._sequence_task = None

    async def wait_detector(self, generation, detector_count, step_started):
        while self.active_sequence and generation == self._sequence_generation:
            if self.detector.status()["count"] != detector_count:
                print("[Magnus] Detected ball, continuing sequence")
                return True
            remaining_ms = int(self.feeder.interval * 1000) - time.ticks_diff(time.ticks_ms(), step_started)
            if remaining_ms <= 0:
                print("[Magnus] Feed interval elapsed, continuing sequence without detection")
                return True
            await asyncio.sleep(min(0.1, remaining_ms / 1000))
        return False

    def save_preset(self, slot):
        launcher = self.launcher.status()
        aimer = self.aimer.status()
        feeder = self.feeder.status()
        current = self.drill_store.list_presets().get(str(slot), {})
        name = current.get("name", "Preset " + str(slot))
        preset = self.drill_store.save_preset(
            slot,
            name,
            {
                "speed": launcher["speed"],
                "spin_angle": launcher["spin_angle"],
                "spin_strength": launcher["spin_strength"],
                "pan": aimer["pan"],
                "tilt": aimer["tilt"],
                "feed_interval": feeder["interval"],
            },
        )
        self.remote_message = "Saved P" + str(slot) + ": " + preset["name"]
        return preset

    def apply_preset(self, slot):
        preset = self.drill_store.get_preset(slot)
        if self.active_sequence:
            self.stop_sequence()
        self.set_settings(
            **preset["settings"],
            launcher_active=False,
            feeder_active=False,
        )
        self.remote_message = "Loaded P" + str(slot) + ": " + preset["name"]
        return preset

    def append_preset(self, slot):
        self.drill_store.get_preset(slot)
        if len(self.sequence_draft) >= 9:
            raise ValueError("A drill can contain at most 9 preset steps")
        self.sequence_draft.append(str(slot))
        self.remote_message = "Added P" + str(slot) + " to drill"
        return len(self.sequence_draft)

    def remove_sequence_step(self):
        if self.sequence_draft:
            self.sequence_draft.pop()
        self.remote_message = "Drill steps: " + str(len(self.sequence_draft))
        return len(self.sequence_draft)

    def clear_sequence_draft(self):
        self.sequence_draft = []
        self.remote_message = "Drill draft cleared"

    def save_sequence(self, slot):
        current = self.drill_store.list_sequences().get(str(slot), {})
        name = current.get("name", "Drill " + str(slot))
        sequence = self.drill_store.save_sequence(
            slot,
            name,
            self.sequence_draft,
        )
        self.remote_message = "Saved D" + str(slot) + " (" + str(len(self.sequence_draft)) + ")"
        return sequence

    def start_saved_sequence(self, slot, randomize_order=False, loop=None, feed_interval=None):
        sequence = self.drill_store.get_sequence(slot)
        if loop is not None:
            self._loop_sequence = loop
        self.set_sequence(sequence)
        self.start_sequence(
            randomize_order=randomize_order,
            feed_interval=self.feeder.interval if feed_interval is None else feed_interval,
            loop=self._loop_sequence,
        )
        self.remote_message = "Running D" + str(slot)
        return True

    def toggle_sequence_loop(self):
        self._loop_sequence = not self._loop_sequence
        self.remote_message = "Drill loop " + ("ON" if self._loop_sequence else "OFF")
        return self._loop_sequence

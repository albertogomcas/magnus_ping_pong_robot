import json
from microdot import Microdot, Response
from machine import Pin, ADC
from ujrpc import JRPCService
import time
from parts import Feeder, Launcher, Aimer, Shaker
import asyncio
import math

class UsedPins():
    PROGRAM = 19  # pullup
    ESC_ALIVE = 36# adc sv
    LAUNCHER_LEFT = 32
    LAUNCHER_TOP = 25
    LAUNCHER_RIGHT = 33
    FEEDER_SERVO = 18
    SHAKER_SERVO = 5
    AIMER_SERVO_V = 17
    AIMER_SERVO_H = 16

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

class Supply():
    def __init__(self):
        self.esc_alive_pin = ADC(Pin(UsedPins.ESC_ALIVE))

    def esc_alive(self):
        return self.esc_alive_pin.read() > 3500



UsedPins.sanity_check()


supply = Supply()
shaker = Shaker(UsedPins.SHAKER_SERVO)
feeder = Feeder(UsedPins.FEEDER_SERVO, shaker=shaker)
feeder.halt()

launcher = Launcher(UsedPins.LAUNCHER_TOP, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT)
launcher.halt()
aimer = Aimer(vaxis=UsedPins.AIMER_SERVO_V, haxis=UsedPins.AIMER_SERVO_H)



def calibrate(launcher):
    launcher.set_speed("all", 100, force=True)
    time.sleep(3)
    launcher.halt()
    launcher.set_speed("all", 0)
    print("Calibrated")
    time.sleep(1)

async def activate(launcher, feeder):
    launcher.activate()
    feeder.activate()

async def halt(launcher, feeder):
    launcher.halt()
    feeder.halt()

async def main():

    launcher.halt()
    feeder.halt()

    feed_task = asyncio.create_task(feeder.run())
    shaker_task = asyncio.create_task(shaker.run())

    offline = False
    calibrated = False

    try:
        previous_active = None

        wait = 0

        while True:
            await asyncio.sleep(0.1)
            active = False

            if not offline and not calibrated:
                value = supply.esc_alive()
                wait += 1

                if value:
                    calibrate(launcher)
                    calibrated = True
                    wait = 0

            topspin = 0 / 10
            sidespin = 0 / 10
            speed = 3 + 5

            if active != previous_active:
                if active:
                    previous_active = True
                    launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)
                    launcher.activate()
                    feeder.activate()

                else:
                    previous_active = False
                    launcher.halt()
                    feeder.halt()

            if not supply.esc_alive():
                calibrated = False
                continue

    except Exception as e:
        launcher.halt()
        feeder.halt()
        feed_task.cancel()
        shaker_task.cancel()
        raise



jrpc = JRPCService(api_version=1)
jrpc.debug = True

pin = Pin(12, Pin.OUT)
pin.off()


Response.default_content_type = 'text/html'

esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return "robopong is ready"

@esp_app.route('/rpc', methods=["POST"])
async def rpc(request):
    return jrpc.handle_rpc(request.json)

@jrpc.fn(name="status")
def status(r):
    status = {
        "launcher": launcher.status(),
        "feeder": feeder.status(),
        "aim": aimer.status(),
    }
    return status

@jrpc.fn(name="feed_one")
def feed_one(r):
    if launcher.active:
        print("Feeding one")
        feeder.feed_one()
    else:
        print("Launcher not active, not feeding")
    return status(r)

@jrpc.fn(name="sync_settings")
def sync_settings(r, settings):
    print(f"Got settings {settings}")

    interval = settings.get("feed_interval", None)
    if interval is not None:
        feeder.set_ball_interval(interval)

    vangle = settings.get("tilt", None)
    hangle = settings.get("pan", None)
    aimer.aim(vangle, hangle)

    speed = settings["speed"]
    spin_angle = settings["spin_angle"]
    spin_strength = settings["spin_strength"]

    topspin = math.cos(math.radians(spin_angle)) * spin_strength / 100
    sidespin = math.sin(math.radians(spin_angle)) * spin_strength / 100

    launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)

    if settings["launcher_active"]:
        pin.on()
        launcher.activate()
    else:
        pin.off()
        feeder.halt()
        launcher.halt()

    if settings["feeder_active"]:
        if launcher.active and launcher.speed > 0:
            feeder.activate()
    else:
        print("Launcher is not running, feeder activation prevented")
        feeder.halt()

    return status(r)
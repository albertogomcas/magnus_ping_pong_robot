from microdot import Microdot, Response
from machine import Pin, ADC
from ujrpc import JRPCService
import time
from arduino import arduino_uart
from parts import Feeder, Launcher, Aimer
import asyncio

class UsedPins():
    PROGRAM = 19  # pullup
    ESC_ALIVE = 36# adc
    LAUNCHER_LEFT = 32
    LAUNCHER_BOTTOM = 33
    LAUNCHER_RIGHT = 25
    FEEDER_SHAKER = 18

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
feeder = Feeder(axis="z", shaker_pin=UsedPins.FEEDER_SHAKER)
feeder.halt()
launcher = Launcher(UsedPins.LAUNCHER_BOTTOM, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT)
launcher.halt()
aimer = Aimer(vaxis="y", haxis="x")



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

    offline = False
    calibrated = False

    try:
        previous_active = None

        wait = 0

        while True:
            await asyncio.sleep(0.1)
            active = True

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
        raise



jrpc = JRPCService(api_version=1)
jrpc.debug = True

pin = Pin(12, Pin.OUT)
pin.off()



@jrpc.fn(name="sync_settings")
def sync_settings(r, settings):
    print(f"Got settings {settings}")

    if settings["active"]:
        pin.on()
        feeder.activate()
    else:
        pin.off()
        feeder.halt()

    bps = settings["feed_rate"]
    feeder.set_ball_interval(1/bps)

    vangle = settings["tilt"]
    hangle = settings["pan"]

    aimer.aim(vangle, hangle)

    return "ok"


@jrpc.fn(name="arduino")
def arduino(r, raw):
    arduino_uart.write(b"\r\n\r\n")
    time.sleep(0.1)
    arduino_uart.flush()
    arduino_uart.write((raw+"\r\n").encode("ascii"))
    time.sleep(0.1)
    ret = arduino_uart.readline()
    print(f"arduino: {ret}")
    return ret

Response.default_content_type = 'text/html'

esp_app = Microdot()

@esp_app.get("/")
async def index(request):
    return "robopong"

@esp_app.route('/rpc', methods=["POST"])
async def rpc(request):
    return jrpc.handle_rpc(request.json)

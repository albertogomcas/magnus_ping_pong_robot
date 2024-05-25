from secrets import Wifi
import asyncio
from time import sleep
from display import Display
from parts import Launcher, Feeder
from primitives import Switch
from machine import Pin, ADC, PWM

class UsedPins():
    PROGRAM = 19  # pullup
    #input
    ACTIVE = 23 # pullup

    MENU = 0 # pullup
    UP = 4 # pullup
    DOWN = 2 # pullup

    ESC_ALIVE = 36# adc

    #i2c
    DISPLAY_SDA = 21 #yellow
    DISPLAY_SCL = 22 #white

    LAUNCHER_LEFT = 32
    LAUNCHER_BOTTOM = 33
    LAUNCHER_RIGHT = 25

    #FEED_1 = 18 # blue
    #FEED_2 = 19 # green
    #FEED_3 = 1 # red
    #FEED_4 = 3 # white

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


UsedPins.sanity_check()

class Supply():
    def __init__(self):
        self.esc_alive_pin = ADC(Pin(UsedPins.ESC_ALIVE))

    def esc_alive(self):
        return self.esc_alive_pin.read() > 2000


async def connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        display.bottom('Wifi...')
        wlan.connect(Wifi.ssid, Wifi.password)
        while not wlan.isconnected():
            await asyncio.sleep(0.1)

    #display.bottom(f"Wifi {wlan.ifconfig()[0]}")

async def launcher_status(launcher):
    global display
    while True:
        display.middle(launcher.status())
        await asyncio.sleep(1)


def calibrate(launcher):
    launcher.set_speed("all", 100, force=True)
    sleep(3)
    launcher.halt()
    launcher.set_speed("all", 0)
    print("Calibrated")
    sleep(1)

async def activate(launcher, feeder):
    launcher.activate()
    feeder.activate()

async def halt(launcher, feeder):
    launcher.halt()
    feeder.halt()

async def main():
    display = Display(sda=UsedPins.DISPLAY_SDA, scl=UsedPins.DISPLAY_SCL)
    supply = Supply()

    def dprint(*args):
        print(*args)
        nonlocal display
        txt = " ".join(args)
        display.middle(txt)
        display.refresh()

    #repl = asyncio.create_task(aiorepl.task())
    c = asyncio.create_task(connect())
    drefresh = asyncio.create_task(display.auto_refresh())

    launcher = Launcher(UsedPins.LAUNCHER_BOTTOM, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT)
    launcher.halt()

    activate_pin = Pin(UsedPins.ACTIVE, Pin.IN, Pin.PULL_UP)
    program_pin = Pin(19, Pin.IN, Pin.PULL_UP)


    activate_sw = Switch(activate_pin)

    #down_button = Pin(UsedPins.DOWN, Pin.IN, Pin.PULL_UP)
    #up_button = Pin(UsedPins.UP, Pin.IN, Pin.PULL_UP)
    #select_button = Pin(UsedPins.MENU, Pin.IN, Pin.PULL_UP)

    #feeder = Feeder([UsedPins.FEED_1, UsedPins.FEED_2, UsedPins.FEED_3, UsedPins.FEED_4])
    #feeder.halt()

    #feed_task = asyncio.create_task(feeder.run())

    offline = False
    calibrated = False

    #lstatus = asyncio.create_task(launcher_status(launcher))

    try:

        choice_index = 0
        choices = ["SPEED", "TOPSPIN", "SIDESPIN"]
        subchoice_index = {"SPEED": 2,
                           "TOPSPIN":  4,
                           "SIDESPIN": 4,
                           }
        subchoices = {
            "SPEED": [1, 2, 3, 4, 5],
            "TOPSPIN": [-8, -6, -4, -2, 0, 2 ,4 ,8],
            "SIDESPIN": [-8, -6, -4, -2, 0, 2 ,4 ,8],
        }

        previous_active = None

        wait = 0

        while True:
            await asyncio.sleep(0.1)
            active = not activate_sw()

            if not offline and not calibrated:
                value = supply.esc_alive()
                dprint(f"Wait {wait//10} ESC:{value}")
                wait += 1

                if value:
                    calibrate(launcher)
                    calibrated = True
                    break
                    wait = 0

            #down = await read_button(down_button, invert = True)
            #up = await read_button(up_button, invert = True)
            #select = await read_button(select_button, invert = True)
            down = False
            up = False
            select = False

            if select:
                choice_index +=1
                if choice_index == len(choices):
                    choice_index = 0

            if up:
                key = choices[choice_index]
                if subchoice_index[key] < len(subchoices[key]) - 1:
                    subchoice_index[key] += 1

            if down:
                key = choices[choice_index]
                if subchoice_index[key] > 0:
                    subchoice_index[key] -= 1

            topspin = subchoices["TOPSPIN"][subchoice_index["TOPSPIN"]] / 10
            sidespin = subchoices["SIDESPIN"][subchoice_index["SIDESPIN"]] / 10
            speed = subchoices["SPEED"][subchoice_index["SPEED"]] + 5

            if active != previous_active:
                if active:
                    previous_active = True
                    launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)
                    launcher.activate()
                    #feeder.activate()
                    display.top(f"A|{choices[choice_index][:2]}|S{speed}T{topspin}D{sidespin}")

                else:
                    previous_active = False
                    launcher.halt()
                    #feeder.halt()
                    display.top(f"H|{choices[choice_index][:2]}|S{speed}T{topspin}D{sidespin}")

            if not supply.esc_alive():
                calibrated = False
                continue

    except Exception as e:
        #feeder.halt()
        drefresh.cancel()
        #lstatus.cancel()
        #feed_task.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()
        raise

from machine import PWM, ADC, Pin
from secrets import Wifi
import asyncio
from time import sleep
from display import Display
from launcher import Launcher
from feeder import Feeder
import _thread
from primitives import Switch


class UsedPins():
    #input
    ACTIVE = 23 # pullup

    MENU = 0 # pullup
    UP = 4 # pullup
    DOWN = 2 # pullup

    ESC_ALIVE = 14 # pulldown

    #i2c
    DISPLAY_SDA = 21 #yellow
    DISPLAY_SCL = 22 #white

    # output
    LED = 32

    LAUNCHER_LEFT = 25
    LAUNCHER_BOTTOM = 26
    LAUNCHER_RIGHT = 27

    FEED_1 = 18 # blue
    FEED_2 = 19 # green
    FEED_3 = 1 # red
    FEED_4 = 3 # white

    @classmethod
    def sanity_check(cls):
        all_numbers = []
        for key, value in cls.__dict__.items():
            if not key.startswith("__"):
                if value in all_numbers:
                    dprint(f"{key} Pin {value} already in use")
                    raise ValueError(f"{key} Pin {value} already in use")
                else:
                    all_numbers.append(value)

display = Display(sda=UsedPins.DISPLAY_SDA, scl=UsedPins.DISPLAY_SCL)

def dprint(*args):
    print(*args)
    global display
    txt = " ".join(args)
    display.middle(txt)
    display.refresh()

UsedPins.sanity_check()

async def connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        display.bottom('Wifi...')
        wlan.connect(Wifi.ssid, Wifi.password)
        while not wlan.isconnected():
            await asyncio.sleep(0.1)

    display.bottom(f"Wifi {wlan.ifconfig()[0]}")



async def read_button(bt, invert = False):
    values = []
    for i in range(2):
        await asyncio.sleep(0.1)
        value = bt.value()
        if invert:
            value = not value
        values.append(value)

    return sum(values) > len(values) / 2


async def launcher_status(launcher):
    global display
    while True:
        display.middle(launcher.status())
        await asyncio.sleep(1)

async def calibrate(launcher, esc_sw):
    while True:
        dprint("Waiting for ESC power up...")
        esc_is_alive = esc_sw()
        if esc_is_alive:
            launcher.set_speed("all", 100, force=True)
            break
        await asyncio.sleep(0.1)

    await asyncio.sleep(3)
    launcher.halt()
    dprint("Calibrated")
    await asyncio.sleep(1)

async def activate(launcher, feeder):
    launcher.activate()
    feeder.activate()

async def halt(launcher, feeder):
    launcher.halt()
    feeder.halt()

async def main():
    #repl = asyncio.create_task(aiorepl.task())
    c = asyncio.create_task(connect())
    drefresh = asyncio.create_task(display.auto_refresh())

    launcher = Launcher(UsedPins.LAUNCHER_BOTTOM, UsedPins.LAUNCHER_LEFT, UsedPins.LAUNCHER_RIGHT)
    launcher.halt()

    activate_pin = Pin(UsedPins.ACTIVE, Pin.IN, Pin.PULL_UP)
    esc_alive_pin = Pin(UsedPins.ESC_ALIVE, Pin.IN, Pin.PULL_DOWN)

    activate_sw = Switch(activate_pin)
    esc_sw = Switch(esc_alive_pin)

    #down_button = Pin(UsedPins.DOWN, Pin.IN, Pin.PULL_UP)
    #up_button = Pin(UsedPins.UP, Pin.IN, Pin.PULL_UP)
    #select_button = Pin(UsedPins.MENU, Pin.IN, Pin.PULL_UP)

    #feeder = Feeder([UsedPins.FEED_1, UsedPins.FEED_2, UsedPins.FEED_3, UsedPins.FEED_4])
    #feeder.halt()

    #feed_task = asyncio.create_task(feeder.run())

    offline = False

    lstatus = asyncio.create_task(launcher_status(launcher))

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

        print(f"esc {esc_sw()}, activate {activate_sw()}")

        previous_active = False

        while True:
            await asyncio.sleep(0.1)
            if not offline:
                if esc_sw():
                    await calibrate(launcher, esc_sw)

            active = not activate_sw()
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

    except Exception as e:
        #feeder.halt()
        drefresh.cancel()
        lstatus.cancel()
        #feed_task.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()
        raise

def main_loop():
    asyncio.run(main())

if __name__ == '__main__':
    sleep(1)
    th = _thread.start_new_thread(main_loop, tuple())
    print("hi")

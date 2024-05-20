from machine import PWM, ADC, Pin
from secrets import Wifi
import asyncio
from time import sleep
from display import Display
from launcher import Launcher
from feeder import Feeder

min_pulse = 1000000  # ns
max_pulse = 2000000  # ns

display = Display(sda=21, scl=22)

def dprint(*args):
    print(*args)
    global display
    txt = " ".join(args)
    display.middle(txt)
    display.refresh()

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



def min_speed(esc):
    dprint("Low speed")
    esc.duty_ns(min_pulse)


def max_speed(esc):
    dprint("MAX speed")
    esc.duty_ns(max_pulse)

def default_speed(esc):
    dprint("High speed")
    esc.duty_ns(min_pulse + (max_pulse - min_pulse) // 30)


async def read_button(bt, invert = False):
    values = []
    for i in range(10):
        await asyncio.sleep(0.01)
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

async def calibrate(launcher, esc_alive):
    while True:
        dprint("Waiting for ESC power up...")
        esc_is_alive = await read_button(esc_alive)
        if esc_is_alive:
            launcher.set_speed("all", 100, force=True)
            break
    await asyncio.sleep(3)
    launcher.halt()
    dprint("Calibrated")
    await asyncio.sleep(1)

async def main():
    c = asyncio.create_task(connect())
    drefresh = asyncio.create_task(display.auto_refresh())

    launcher = Launcher(25, 26, 27)
    launcher.halt()
    feeder = Feeder(pin=15)
    feeder.halt()

    min_button = Pin(13, Pin.IN, Pin.PULL_DOWN)
    max_button = Pin(12, Pin.IN, Pin.PULL_DOWN)
    esc_alive = Pin(33, Pin.IN, Pin.PULL_DOWN)
    down_button = Pin(17, Pin.IN, Pin.PULL_UP)
    up_button = Pin(18, Pin.IN, Pin.PULL_UP)
    select_button = Pin(19, Pin.IN, Pin.PULL_UP)

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


        while True:
            await asyncio.sleep(0.05)
            if not offline:
                if not await read_button(esc_alive):
                    await calibrate(launcher, esc_alive)

            min_pressed = await read_button(min_button)
            max_pressed = await read_button(max_button)
            down = await read_button(down_button, invert = True)
            up = await read_button(up_button, invert = True)
            select = await read_button(select_button, invert = True)

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

            display.top(f"{choices[choice_index][:2]}|S{speed}T{topspin}D{sidespin}")

            if max_pressed:
                launcher.configure(speed=speed, topspin=topspin, sidespin=sidespin)
                launcher.activate()
                feeder.activate()

            if min_pressed:
                launcher.halt()
                feeder.halt()


    except Exception as e:
        feeder.halt()
        drefresh.cancel()
        lstatus.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()
        raise

if __name__ == '__main__':
    asyncio.run(main())

from machine import PWM, ADC, Pin
from secrets import Wifi
import asyncio
from time import sleep
from display import Display
from launcher import Launcher

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

    min_button = Pin(13, Pin.IN, Pin.PULL_DOWN)
    max_button = Pin(12, Pin.IN, Pin.PULL_DOWN)
    esc_alive = Pin(33, Pin.IN, Pin.PULL_DOWN)
    a_button = Pin(17, Pin.IN, Pin.PULL_UP)
    b_button = Pin(18, Pin.IN, Pin.PULL_UP)
    c_button = Pin(19, Pin.IN, Pin.PULL_UP)

    offline = True
    if not offline:
        if not await read_button(esc_alive):
            await calibrate(launcher, esc_alive)

    lstatus = asyncio.create_task(launcher_status(launcher))

    try:

        while True:
            await asyncio.sleep(0.1)
            min_pressed = await read_button(min_button)
            max_pressed = await read_button(max_button)
            a = await read_button(a_button, invert = True)
            b = await read_button(b_button, invert = True)
            c = await read_button(c_button, invert = True)

            buttons = ""
            buttons += "A" if a else "_"
            buttons += "B" if b else "_"
            buttons += "C" if c else "_"

            display.top(buttons)

            if "A" in buttons:
                launcher.ease()

            if "B" in buttons:
                launcher.activate()

            if "C" in buttons:
                topspin = 0.5
            else:
                topspin = 0

            if max_pressed:
                launcher.configure(5, topspin=topspin, sidespin=0)
                launcher.activate()

            if min_pressed:
                launcher.halt()


    except Exception as e:
        drefresh.cancel()
        lstatus.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()

if __name__ == '__main__':
    asyncio.run(main())

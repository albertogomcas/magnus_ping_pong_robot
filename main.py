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


async def read_button(bt):
    if bt.value():
        for i in range(10):
            await  asyncio.sleep(0.02)
            if bt.value():
                continue
            else:
                return False
        return True

    return False

async def launcher_status(launcher):
    global display
    while True:
        display.middle(launcher.status())
        await asyncio.sleep(1)


async def main():
    c = asyncio.create_task(connect())
    drefresh = asyncio.create_task(display.auto_refresh())

    launcher = Launcher(25, 26, 27)

    lstatus = asyncio.create_task(launcher_status(launcher))

    try:
        min_button = Pin(32, Pin.IN, Pin.PULL_DOWN)
        max_button = Pin(12, Pin.IN, Pin.PULL_DOWN)


        while True:
            await asyncio.sleep(0.1)
            min_pressed = await read_button(min_button)
            max_pressed = await read_button(max_button)

            if min_pressed and not max_pressed:
                launcher.set_speed("all", 5)
                launcher.configure(9, topspin=0, sidespin=1)
                launcher.activate()

            if max_pressed and not min_pressed:
                launcher.halt()


    except Exception as e:
        drefresh.cancel()
        lstatus.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()

if __name__ == '__main__':
    asyncio.run(main())

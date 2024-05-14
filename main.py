import os
import sys
from machine import PWM, ADC, Pin
import ssd1306
from secrets import Wifi
import asyncio
from time import sleep
from display import Display

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


async def main():
    c = asyncio.create_task(connect())
    drefresh = asyncio.create_task(display.auto_refresh())

    try:
        calibrate = False

        min_button = Pin(32, Pin.IN, Pin.PULL_DOWN)
        max_button = Pin(12, Pin.IN, Pin.PULL_DOWN)
        esc_pin = Pin(33, Pin.OUT)
        poti = ADC(0)

        esc = PWM(esc_pin, freq=50)

        if calibrate:
            max_speed(esc)
            dprint("Turn on the ESC now")
            dprint("Press min button when the max is calibrated")
            while not await read_button(min_button):
                sleep(0.1)
            dprint("Turn off the ESC")
            calibrate = False

        min_speed(esc)

        a = 1 / 0

        while True:
            await asyncio.sleep(0.1)
            min_pressed = await read_button(min_button)
            max_pressed = await read_button(max_button)

            if min_pressed and not max_pressed:
                min_speed(esc)

            if max_pressed and not min_pressed:
                default_speed(esc)



    except Exception as e:
        #fname = exc_tb.tb_frame.f_code.co_filename
        drefresh.cancel()
        display.top(f"Exception")
        display.middle(f"{e}")
        display.refresh()

if __name__ == '__main__':
    asyncio.run(main())

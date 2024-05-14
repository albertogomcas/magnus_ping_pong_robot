import time
import utime
from machine import Pin, PWM, ADC, SoftI2C
import ssd1306
from secrets import Wifi
import asyncio
from time import sleep

min_pulse = 1000000  # ns
max_pulse = 2000000  # ns

i2c = SoftI2C(sda=Pin(21), scl=Pin(22))
display = ssd1306.SSD1306_I2C(128, 32, i2c)
display.text("Starting up", 0, 0, 1)
display.show()
time.sleep(1)


def dprint(*args):
    print(*args)
    global display
    display.fill(0)
    display.show()
    txt = " ".join(args)
    lines = txt.split("\n")
    for index, line in enumerate(lines):
        display.text(line, 0, index*9, 1)
    display.show()


# def do_connect():
#     import network
#     wlan = network.WLAN(network.STA_IF)
#     wlan.active(True)
#     if not wlan.isconnected():
#         print('connecting to network...')
#         wlan.connect(Wifi.ssid, Wifi.password)
#         while not wlan.isconnected():
#             pass
#     print('network config:', wlan.ifconfig())


def min_speed(esc):
    dprint("set min\nspeed")
    esc.duty_ns(min_pulse)


def max_speed(esc):
    dprint("set max\nspeed")
    esc.duty_ns(max_pulse)

def default_speed(esc):
    dprint("set default")
    esc.duty_ns(min_pulse + (max_pulse - min_pulse) // 30)

def sweep(esc):
    dprint("sweep")
    span = max_pulse - min_pulse
    steps = 20

    for i in range(steps):
        duty = min_pulse + (i * span) // steps
        dprint(f"step {i} Duty {duty}ns ({(duty - min_pulse) / span * 100}%)")
        esc.duty_ns(duty)
        sleep(0.5)

    min_speed(esc)


def read_button(bt):
    if bt.value():
        for i in range(10):
            sleep(0.02)
            if bt.value():
                continue
            else:
                return False
        return True

    return False


def main():
    # do_connect()

    calibrate = False

    min_button = Pin(32, Pin.PULL_DOWN)
    max_button = Pin(12, Pin.PULL_DOWN)
    esc_pin = Pin(33, Pin.OUT)
    poti = ADC(0)

    esc = PWM(esc_pin, freq=50)

    if calibrate:
        max_speed(esc)
        dprint("Turn on the ESC now")
        dprint("Press min button when the max is calibrated")
        while not read_button(min_button):
            sleep(0.1)
        dprint("Turn off the ESC")
        calibrate = False

    min_speed(esc)

    while True:
        utime.sleep_ms(200)
        min_pressed = read_button(min_button)
        max_pressed = read_button(max_button)

        if min_pressed and not max_pressed:
            min_speed(esc)

        if max_pressed and not min_pressed:
            default_speed(esc)

        if min_pressed and max_pressed:
            sweep(esc)


if __name__ == '__main__':
    dprint("Hi")
    main()
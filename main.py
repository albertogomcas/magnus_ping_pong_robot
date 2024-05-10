import utime
from machine import Pin
from secrets import Wifi
import asyncio

def do_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(Wifi.ssid, Wifi.password)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

def main():
    #do_connect()

    led = Pin(27, Pin.OUT)
    enabled = False
    while True:
        if enabled:
            led.off()
        else:
            led.on()
        utime.sleep_ms(1000)
        enabled = not enabled

if __name__ == '__main__':
    print("Hi")
    main()
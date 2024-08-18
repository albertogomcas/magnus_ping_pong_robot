from machine import Pin
import network
from secrets import Wifi
from webmain import esp_app, main
import asyncio

def connect():
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    nic.connect(Wifi.ssid, Wifi.password)
    nic.ifconfig(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))
    print(nic.isconnected())
    print(nic.ifconfig())

def run():
    asyncio.create_task(main())
    esp_app.run(port=80, debug=True)


program_pin = Pin(19, Pin.IN, Pin.PULL_UP)

if not program_pin.value():
    print("Stop program")
else:
    print("Continue program")
    connect()
    try:
        run()
    except:
        esp_app.shutdown()
        raise








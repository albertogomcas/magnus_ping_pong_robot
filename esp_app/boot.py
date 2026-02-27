from machine import UART, Pin
import gc
import dev
import json
import os
import network
from secrets import Wifi
import time

def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False

def connect():
    nic = network.WLAN(network.STA_IF)
    nic.active(True)
    nic.connect(Wifi.ssid, Wifi.password)
    nic.ifconfig(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))
    print(f"{nic.isconnected()=}")
    print(f"{nic.ifconfig()=}")
    start = time.time()
    while time.time() - start < 10:
        if nic.isconnected():
            break
    else:
        raise RuntimeWarning("Could not connect to network")


try:
    if exists("custom_boot.json"):
        with open("custom_boot.json") as f:
            boot = json.load(f)
        print(f"Found custom one-time boot settings {boot}")
        os.remove("custom_boot.json")

    elif exists("default_boot.json"):
        with open("default_boot.json") as f:
            boot = json.load(f)
        print(f"Using default boot settings {boot}")
    else:
        print("No boot instructions found")
        boot = None

    if boot:
        dev.DevFlags.simulation_mode = boot["simulation_mode"]
        dev.DevFlags.run_app = boot["run_app"]
except:
    raise

# Pre-allocate UART1 at the end of boot.py - all other boot imports are done,
# but main.py (and its heavy imports) hasn't run yet.
# We store it directly in the magnus module variable so it survives reliably.
gc.collect()
try:
    _tmp = UART(1)
    _tmp.deinit()
except:
    pass
import magnus
magnus._preallocated_uart = UART(1, baudrate=1000000,
                                  tx=Pin(23),  # UsedPins.ST_SERVO_TX
                                  rx=Pin(22),  # UsedPins.ST_SERVO_RX
                                  rxbuf=256, txbuf=256)
print("[boot] UART pre-allocated OK")


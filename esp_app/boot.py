import dev
import json
import os
import network
from esp_app.secrets import Wifi
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

connect()

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

        if boot["update_app"]:
            dev.update()

except:
    raise

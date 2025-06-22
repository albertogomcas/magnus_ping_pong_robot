from datetime import datetime
from shiny import ui, reactive, render, session
import requests
import json
import os
import matplotlib.pyplot as plt

# Robot URL
robot_url = "http://10.0.0.47"
PRESET_FILE = "presets.json"

def save_current_settings(settings):
    """Save current settings to a file"""
    with open("current_settings.json", "w") as f:
        json.dump(settings, f)

def load_current_settings():
    """Load current settings from file if it exists"""
    if os.path.exists("current_settings.json"):
        with open("current_settings.json", "r") as f:
            return json.load(f)
    return None

def save_preset_to_file(name, preset):
    """ Save the preset to a JSON file """
    presets = load_presets_from_file()
    presets[name] = preset
    with open(PRESET_FILE, "w") as f:
        json.dump(presets, f)

def load_presets_from_file():
    """ Load the preset from a JSON file if it exists """
    if os.path.exists(PRESET_FILE):
        with open(PRESET_FILE, "r") as f:
            return json.load(f)
    return {}

# Function to sync settings with the robot
def sync_settings(feeder_active, launcher_active, speed, spin_angle, spin_strength, pan, tilt, feed_interval, shaker_f=None, shaker_r=None):
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "sync_settings",
        "params": {
            "settings": {
                "feeder_active": feeder_active,
                "launcher_active": launcher_active,
                "speed": speed,
                "spin_angle": spin_angle,
                "spin_strength": spin_strength,
                "pan": pan,
                "tilt": tilt,
                "feed_interval": feed_interval,
                "shaker_f": shaker_f,
                "shaker_r": shaker_r,
            }
        },
        "id": 1,
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
    return response.json()

def set_sequence(sequence):
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "set_sequence",
        "params": {
            "sequence": sequence,
            },
        "id": 17,
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
    return response.json()

def start_sequence(settings):
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "start_sequence",
        "params": {
            "settings": settings,
        },
        "id": 18,
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
    return response.json()

def stop_sequence():
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "stop_sequence",
        "id": 19,
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
    return response.json()

# Function to check robot status
def robot_status():
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "status",
        "id": 2,
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=0.25)
        status = response.json()
        status["online"] = True
        return status

    except requests.exceptions.Timeout:
        return dict(online=False)

# Common styles
app_styles = ui.tags.style("""
    .shiny-input-container.switch label {
        font-size: 1.4em;
    }

    .form-check.form-switch .form-check-input {
        transform: scale(1.5);
        margin-right: 10px;
    }
""")
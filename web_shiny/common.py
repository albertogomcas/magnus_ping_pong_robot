from datetime import datetime
from shiny import ui, reactive, render, session
import requests
import json
import os
import matplotlib.pyplot as plt
from threading import Timer, Lock

# Robot URL
robot_url = "http://10.0.0.47"
PRESET_FILE = "presets.json"

class SettingsBatcher:
    """
    Batches rapid setting updates to prevent network flooding.
    When settings change rapidly (e.g., slider dragging), this class
    debounces the updates and sends only the final values.
    """
    def __init__(self, callback, delay=0.3):
        """
        Args:
            callback: Function to call with batched settings
            delay: Time in seconds to wait before sending (debounce delay)
        """
        self._callback = callback
        self._delay = delay
        self._pending = {}
        self._timer = None
        self._lock = Lock()

    def update(self, **kwargs):
        """Add settings to the batch. Will be sent after delay period."""
        with self._lock:
            self._pending.update(kwargs)

            # Cancel existing timer if one is running
            if self._timer is not None:
                self._timer.cancel()

            # Start new timer
            self._timer = Timer(self._delay, self._flush)
            self._timer.start()

    def _flush(self):
        """Send the batched settings."""
        with self._lock:
            if self._pending:
                try:
                    print(f"Batching: Sending batched settings: {self._pending}")
                    self._callback(**self._pending)
                except Exception as e:
                    print(f"Batching: Error sending settings: {e}")
                finally:
                    self._pending.clear()
                    self._timer = None

    def flush_now(self):
        """Immediately flush pending settings without waiting for timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._flush()

# Global batcher instance (will be initialized in control panel)
_settings_batcher = None

def get_settings_batcher():
    """Get or create the global settings batcher instance."""
    global _settings_batcher
    if _settings_batcher is None:
        _settings_batcher = SettingsBatcher(
            callback=lambda **kw: sync_settings(**kw),
            delay=0.3  # 300ms debounce - good balance between responsiveness and efficiency
        )
    return _settings_batcher


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

def delete_preset_from_file(preset_name):
    presets = load_presets_from_file()
    if preset_name in presets:
        del presets[preset_name]
        with open('presets.json', 'w') as f:
            json.dump(presets, f)

# --------------------------------------------------------------------------- #
#  Low-level RPC helper
# --------------------------------------------------------------------------- #

def rpc_call(method, params=None, rpc_id=1, timeout=2):
    """Send a single JSON-RPC 2.0 request and return the parsed response."""
    url = robot_url + "/rpc"
    payload = {"jsonrpc": "2.0", "method": method, "id": rpc_id}
    if params is not None:
        payload["params"] = params
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=timeout)
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout calling {method}")
        return {"error": "timeout"}
    except Exception as e:
        print(f"Error calling {method}: {e}")
        return {"error": str(e)}

# --------------------------------------------------------------------------- #
#  Granular setters  (each touches only the parameter it owns)
# --------------------------------------------------------------------------- #

def set_speed(speed):
    return rpc_call("set_launcher", {"speed": speed})

def set_spin(spin_angle, spin_strength):
    return rpc_call("set_launcher", {"spin_angle": spin_angle, "spin_strength": spin_strength})

def set_aim(tilt=None, pan=None):
    params = {}
    if tilt is not None:
        params["tilt"] = tilt
    if pan is not None:
        params["pan"] = pan
    return rpc_call("set_aim", params)

def set_feed_interval(interval):
    return rpc_call("set_feed_interval", {"interval": interval})

def activate():
    return rpc_call("activate")

def halt():
    return rpc_call("halt")

# --------------------------------------------------------------------------- #
#  Legacy full-state sync  (kept for drill / preset apply)
# --------------------------------------------------------------------------- #

# Function to sync settings with the robot
def sync_settings(feeder_active, launcher_active, speed, spin_angle, spin_strength, pan, tilt, feed_interval):
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
            }
        },
        "id": 1,
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=2)
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout syncing settings to robot")
        return {"error": "timeout"}
    except Exception as e:
        print(f"Error syncing settings: {e}")
        return {"error": str(e)}

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
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=2)
        return response.json()
    except Exception as e:
        print(f"Error setting sequence: {e}")
        return {"error": str(e)}

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
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=2)
        return response.json()
    except Exception as e:
        print(f"Error starting sequence: {e}")
        return {"error": str(e)}

def stop_sequence():
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "stop_sequence",
        "id": 19,
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=2)
        return response.json()
    except Exception as e:
        print(f"Error stopping sequence: {e}")
        return {"error": str(e)}

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
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
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
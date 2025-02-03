import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import time
import asyncio

# Robot URL
robot_url = "http://10.0.0.47"

# Describe the parameters of the robot
params = {
    "active": ["bool", None, False],
    "speed": ["int", (0, 100), 0],
    "spin_angle": ["int", (-180, 180), 0],
    "spin_strength": ["int", (0, 100), 0],
    "pan": ["float", (-20, 20), 0],
    "tilt": ["float", (-10, 10), 0],
    "feed_interval": ["int", (1, 10)],
}

# Initialize session state for presets if not already done
if "presets" not in st.session_state:
    st.session_state.presets = [
        {"speed": 30, "spin_angle": 0, "spin_strength": 0, "pan": 0, "tilt": 10},
        {"speed": 60, "spin_angle": 90, "spin_strength": 50, "pan": 0, "tilt": 10},
    ]


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
    response = requests.post(url, headers=headers, json=payload, verify=False)
    return response.json()

def feed_one():
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": "feed_one",
        "id": 3,
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, headers=headers, json=payload, verify=False)
    return response.json()

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


# Function to save preset
def save_preset(speed, spin_angle, spin_strength, pan, tilt):
    preset = {
        "speed": speed,
        "spin_angle": spin_angle,
        "spin_strength": spin_strength,
        "pan": pan,
        "tilt": tilt,
    }
    st.session_state.presets.append(preset)  # Save to session state
    st.success("Preset saved successfully!")


# Function to apply preset to controls
def apply_preset(preset):
    st.session_state.speed = preset["speed"]
    st.session_state.spin_angle = preset["spin_angle"]
    st.session_state.spin_strength = preset["spin_strength"]
    st.session_state.pan = preset["pan"]
    st.session_state.tilt = preset["tilt"]

    response = sync_settings(
        launcher_active=st.session_state.get("launcher_active", False),
        feeder_active=st.session_state.get("feeder_active", False),
        speed=st.session_state.speed,
        spin_angle=st.session_state.spin_angle,
        spin_strength=st.session_state.spin_strength,
        pan=st.session_state.pan,
        tilt=st.session_state.tilt,
        feed_interval=st.session_state.get("feed_interval", 5),
    )

    st.rerun()

def remove_preset(index):
    del st.session_state.presets[index]
    st.success(f"Preset {index+1} deleted")

st.set_page_config(page_title="RoboPong WebUI", layout="wide")

#refresh = st_autorefresh(interval=2000, key="status")


# Streamlit UI Layout
st.title("RoboPong WebUI")

col1, col2, col3 = st.tabs(["Status", "Control", "Presets"])

response = robot_status()
if response["online"]:
    st.info("RoboPong is online")
else:
    st.error("RoboPong is offline")

with col1:
    st.header("Status")
    if response["online"]:
        status = response["result"]
        launcher_t = st.toggle("Launcher", value=status["launcher"]["active"], disabled=True, key="launcher_status")
        feeder_t = st.toggle("Feeder", value=status["feeder"]["active"], disabled=True, key="feeder_status")
        st.write(response["result"])
    else:
        st.error("RoboPong is offline")



with col2:
    # Control section
    st.header("Control")
    launcher_active = st.toggle("Launcher", value=False)
    feeder_active = st.toggle("Feeder", value=False)

    speed = st.slider("Speed", min_value=0, max_value=100, step=1, value=st.session_state.get("speed", 0))
    spin_angle = st.slider("Spin Angle", min_value=-180, max_value=180, step=15,
                           value=st.session_state.get("spin_angle", 0))
    spin_strength = st.slider("Spin Strength", min_value=0, max_value=100, step=20,
                              value=st.session_state.get("spin_strength", 0))
    pan = st.slider("Launcher Pan", min_value=-10, max_value=10, step=1, value=st.session_state.get("pan", 0))
    tilt = st.slider("Launcher Tilt", min_value=-10, max_value=35, step=1, value=st.session_state.get("tilt", 10))
    feed_interval = st.slider("Ball Feed Interval", min_value=1, max_value=10, step=1,
                              value=st.session_state.get("feed_interval", 5))

    if st.button("Feed one"):
        response = sync_settings(
            feeder_active=feeder_active,
            launcher_active=launcher_active,
            speed=speed,
            spin_angle=spin_angle,
            spin_strength=spin_strength,
            pan=pan,
            tilt=tilt,
            feed_interval=feed_interval,
        )
        feed_one()


    # Button to sync settings with robot
    if st.button("Send settings"):
        response = sync_settings(
            feeder_active=feeder_active,
            launcher_active=launcher_active,
            speed=speed,
            spin_angle=spin_angle,
            spin_strength=spin_strength,
            pan=pan,
            tilt=tilt,
            feed_interval=feed_interval,
        )
        st.json(response)  # Show response from robot
        st.rerun()

    # Button to save preset
    if st.button("Save preset"):
        save_preset(speed, spin_angle, spin_strength, pan, tilt)

with col3:
    # Display presets
    st.header("Presets")
    if st.session_state.presets:
        for index, preset in enumerate(st.session_state.presets):
            # Display preset values
            st.write(
                f"Preset {index + 1} - Speed: {preset['speed']}, Spin: {preset['spin_strength']}% {preset['spin_angle']}°, Aim: T{preset['tilt']} P{preset['pan']}")

            # Add a button to apply the preset to controls
            if st.button(f"Apply Preset {index + 1}", key=f"apply_{index}"):
                apply_preset(preset)
                st.success(f"Preset {index + 1} applied!")

            # Add a button to remove the preset
            if st.button(f"Remove Preset {index + 1}", key=f"remove_{index}"):
                remove_preset(index)

    else:
        st.write("No presets saved yet.")
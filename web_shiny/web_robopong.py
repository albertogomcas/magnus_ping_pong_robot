from datetime import datetime
from shiny import App, ui, reactive, render
import requests
import json

# Robot URL
robot_url = "http://10.0.0.47"


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


# Shiny UI layout
app_ui = ui.page_fluid(
    ui.h2("RoboPong WebUI"),

    ui.page_navbar(
        ui.nav_panel("Status",  # First tab
                     ui.output_ui("status_ui")
                     ),
        ui.nav_panel("Control",  # Second tab
                     ui.input_switch("launcher_active", "Launcher Active", False),
                     ui.input_switch("feeder_active", "Feeder Active", False),
                     ui.input_slider("speed", "Speed", min=0, max=100, value=0),
                     ui.input_slider("spin_angle", "Spin Angle", min=-180, max=180, value=0, step=10),
                     ui.input_slider("spin_strength", "Spin Strength", min=0, max=100, value=0, step=10),
                     ui.input_slider("pan", "Launcher Pan", min=-10, max=10, value=0, step=1),
                     ui.input_slider("tilt", "Launcher Tilt", min=-10, max=35, value=10, step=1),
                     ui.input_slider("feed_interval", "Ball Feed Interval (s)", min=1, max=10, value=5),
                     ui.input_action_button("feed_one", "Feed One")
                     ),
        ui.nav_panel("Presets",  # Third tab
                     ui.input_action_button("save_preset", "Save Preset")
                     ),
        title="RoboPong",
    )
)


# Shiny server logic
def server(input, output, session):
    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        reactive.invalidate_later(1) # refresh every 1 second
        status = robot_status()
        if status["online"]:
            return ui.div(
                ui.p(f"{datetime.now().strftime('%H:%M:%S')} Robot is online!"),
                ui.markdown(str(status))
            )
        else:
            return ui.p(f"{datetime.now().strftime('%H:%M:%S')} RoboPong is offline")

    # Handle the "Send Settings" button press
    @reactive.Effect
    def send_settings():
        response = sync_settings(
            feeder_active=input.feeder_active(),
            launcher_active=input.launcher_active(),
            speed=input.speed(),
            spin_angle=input.spin_angle(),
            spin_strength=input.spin_strength(),
            pan=input.pan(),
            tilt=input.tilt(),
            feed_interval=input.feed_interval()
        )
        print(response)  # Output response for debugging
        return ui.notification_show("Settings sent to RoboPong!", type="success")

    # Handle the "Feed One" button press
    @reactive.Effect
    def feed_one():
        if input.feed_one():
            url = robot_url + "/rpc"
            payload = {
                "jsonrpc": "2.0",
                "method": "feed_one",
                "id": 3,
            }
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, json=payload, verify=False)

            return ui.notification_show(f"Feeding one ball...{response.json()}", type="info")

    # Handle the "Save Preset" button press
    @reactive.Effect
    def save_preset():
        if input.save_preset():
            # Save current settings as preset
            preset = {
                "speed": input.speed(),
                "spin_angle": input.spin_angle(),
                "spin_strength": input.spin_strength(),
                "pan": input.pan(),
                "tilt": input.tilt(),
            }
            print(f"Preset saved: {preset}")
            return ui.notification_show("Preset saved!", type="success")


# Create the Shiny app
app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app('web_robopong:app', reload=True)





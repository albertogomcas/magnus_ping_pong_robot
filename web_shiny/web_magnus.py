from datetime import datetime
from shiny import App, ui, reactive, render, session
import requests
import json
import os
import matplotlib.pyplot as plt
from drill import app_ui as drill_app

# Robot URL
robot_url = "http://10.0.0.47"
PRESET_FILE = "presets.json"

current_sequence_index = reactive.Value(0)
sequence_running = reactive.Value(False)

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
def sync_settings(feeder_active, launcher_active, speed, spin_angle, spin_strength, pan, tilt, feed_interval, shaker):
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
                "shaker": shaker,
            }
        },
        "id": 1,
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



# Shiny UI layout
app_ui = ui.page_fluid(
    ui.h2("Magnus WebUI"),
    ui.tags.style("""
        .shiny-input-container.switch label {
            font-size: 1.4em;
        }
    
        .form-check.form-switch .form-check-input {
            transform: scale(1.5);
            margin-right: 10px;
        }
    """),
    ui.page_navbar(
        ui.nav_panel("Control",  # Second tab
                    ui.output_ui("status_ui"),
                     ui.input_switch("launcher_active", "Launcher Active", False),
                     ui.input_slider("speed", "Speed", min=0, max=100, value=0),
                     ui.div(
                        ui.input_slider("spin_angle", "Spin Angle", min=-180, max=180, value=0, step=10),
                            ui.input_slider("spin_strength", "Spin Strength", min=0, max=100, value=0, step=10),
                         style="display: flex; gap: 20px;",
                     ),
                     ui.div(
                     ui.input_slider("pan", "Launcher Pan", min=-20, max=20, value=0, step=1),
                     ui.input_slider("tilt", "Launcher Tilt", min=-20, max=35, value=0, step=1),
                    style="display: flex; gap: 20px;",
                     ),
                     ui.input_action_button("save_preset", "Save Preset"),
                     ui.hr(),
                     ui.input_switch("feeder_active", "Continuous Feed", False),
                     ui.input_slider("feed_interval", "Ball Feed Interval (s)", min=1, max=10, value=5, step=0.5),
                     ui.input_slider("shaker_tuning", "Shaker tuning", min=-100, max=100, value=0, step=1),

                     ),
        ui.nav_panel("Presets",  # Third tab
                     ui.output_ui("preset_dropdown_ui"),
                     ui.output_ui("preset_ui"),
                     ),
        ui.nav_panel(
            "Target",
            ui.output_plot("table", width="400px", height="400px"),
            ui.output_text("click_info"),
        ),
        ui.nav_panel(
            "drill",
            drill_app,
        ),
        ui.nav_panel(
          "Calibrate",
            ui.input_action_button("calibrate_btn", "Calibrate Aim Zero"),
        ),
        ui.nav_panel(
          "Dev",
            ui.input_action_button("reset", "Reset ESP32"),
            ui.input_action_button("enable_simulation", "Enable simulation mode"),
            ui.input_action_button("disable_simulation", "Disable simulation mode"),
            ui.input_action_button("interrupt_server", "Interrupt jRPC server"),
        ),
        title=ui.output_text("status_navbar_ui"),
        id="main_tab",
    )
)

# Shiny server logic
def server(input, output, session):
    session.robot_status_text = reactive.value("🔴 Offline")
    session.preset_list = reactive.value([])
    session.selected_preset = reactive.value("")
    session.preset_summary = reactive.value("No preset loaded")
    session.current_preset_name = reactive.value("")
    first_run = True


    # Display current preset
    @output
    @render.text
    def current_preset():
        if session.sequence_active() and session.current_preset_name():
            return f"Current preset: {session.current_preset_name()}"
        return ""

    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        reactive.invalidate_later(1) # refresh every 1 second
        status = robot_status()
        #status = {"online": False}
        print(status)
        if status["online"]:
            supply_on = status["result"]["supply"]["esc_alive"]
            if supply_on:
                session.robot_status_text.set("🟢⚡")
            else:
                session.robot_status_text.set("🟢💤")
            return ui.div(
                ui.p(f"{datetime.now().strftime('%H:%M:%S')} Robot is online!"),
            )
        else:
            print("Offline")
            session.robot_status_text.set("🔴 Offline")
            return ui.p(f"{datetime.now().strftime('%H:%M:%S')} RoboPong is offline")

    @output
    @render.text
    def status_navbar_ui():
        return session.robot_status_text()

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
            feed_interval=input.feed_interval(),
            shaker=input.shaker_tuning(),
        )
        print(response)  # Output response for debugging
        return ui.notification_show("Settings sent to RoboPong!", type="success", duration=0.25)

    @reactive.Effect
    @reactive.event(input.reset)
    def reset():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "reset",
            "id": 5,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Reset command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Reset command failed: {e}")
            ui.notification_show("Reset command failed.", type="error", duration=1)

    @reactive.Effect
    @reactive.event(input.interrupt_server)
    def interrupt_server():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "interrupt",
            "id": 5,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Interrupt command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Interrupt command failed: {e}")
            ui.notification_show("Interrupt command failed.", type="error", duration=1)

    @reactive.Effect
    @reactive.event(input.enable_simulation)
    def enable_simulation():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "enable_simulation",
            "id": 7,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Command failed: {e}")
            ui.notification_show("Command failed.", type="error", duration=1)

    @reactive.Effect
    @reactive.event(input.disable_simulation)
    def disable_simulation():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "disable_simulation",
            "id": 9,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Command failed: {e}")
            ui.notification_show("Command failed.", type="error", duration=1)

    @reactive.effect
    @reactive.event(input.calibrate_btn)
    def calibrate_aim_zero():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "calibrate_aim_zero",
            "id": 4,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Calibration command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Calibration failed: {e}")
            ui.notification_show("Calibration failed.", type="error", duration=1)

    # Handle the "Save Preset" button press
    @reactive.Effect
    def save_preset():
        if input.save_preset():
            # Save current settings as preset
            modal = ui.modal(
                ui.input_text("preset_name", "Enter preset name"),
                ui.input_action_button("ok_preset_name", "OK"),
            )
            ui.modal_show(modal)


    @reactive.effect
    @reactive.event(input.ok_preset_name)
    def __():
        ui.modal_remove()
        preset = {
            "speed": input.speed(),
            "spin_angle": input.spin_angle(),
            "spin_strength": input.spin_strength(),
            "pan": input.pan(),
            "tilt": input.tilt(),
        }
        save_preset_to_file(input.preset_name(), preset)
        session.preset_list.set(list(load_presets_from_file().keys()))
        print(f"Preset saved: {preset}")
        ui.notification_show("Preset saved!", type="success", duration=0.25)
        session.preset_summary.set(f"Saved Preset: {input.preset_name()}")


    @output()
    @render.ui
    def preset_ui():
        return ui.p(session.preset_summary())

    @reactive.Effect
    def load_preset():
        presets = load_presets_from_file()
        preset_name = input.preset_dropdown()
        if preset_name and preset_name in presets:
            preset = presets[preset_name]
            session.selected_preset.set(preset_name)  # Store selection
            session.preset_summary.set(f"Loaded Preset: {preset_name} - {preset}")

            # Set UI controls to preset values
            ui.update_slider("speed", value=preset["speed"])
            ui.update_slider("spin_angle", value=preset["spin_angle"])
            ui.update_slider("spin_strength", value=preset["spin_strength"])
            ui.update_slider("pan", value=preset["pan"])
            ui.update_slider("tilt", value=preset["tilt"])

    @reactive.Effect
    def load_presets_on_startup():
        session.preset_list.set(list(load_presets_from_file().keys()))

    @output()
    @render.ui
    def preset_dropdown_ui():
        return ui.input_select("preset_dropdown", "Select Preset", choices=session.preset_list())

    @output
    @render.plot
    def plot():
        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_title("Click anywhere")
        ax.grid(True)
        return fig

    @output
    @render.text
    def click_info():
        if input.plot_click():
            click_data = input.plot_click()
            return f"Clicked at: x={click_data['x']:.2f}, y={click_data['y']:.2f}"
        return "Click on the plot to see coordinates."

    @reactive.Effect
    def load_settings_on_startup():
        nonlocal first_run
        if first_run:
            first_run = False
            print("First run, loading settings")
        else:
            return
        settings = load_current_settings()
        if settings:
            ui.update_switch("launcher_active", value=False) #settings.get("launcher_active", False))
            ui.update_slider("speed", value=settings.get("speed", 0))
            ui.update_slider("spin_angle", value=settings.get("spin_angle", 0))
            ui.update_slider("spin_strength", value=settings.get("spin_strength", 0))
            ui.update_slider("pan", value=settings.get("pan", 0))
            ui.update_slider("tilt", value=settings.get("tilt", 0))
            ui.update_switch("feeder_active", value=settings.get("feeder_active", False))
            ui.update_slider("feed_interval", value=settings.get("feed_interval", 5))
            ui.update_slider("shaker_tuning", value=settings.get("shaker_tuning", 0))

    # Save settings whenever they change
    @reactive.Effect
    def save_settings_on_change():
        settings = {
            "launcher_active": input.launcher_active(),
            "speed": input.speed(),
            "spin_angle": input.spin_angle(),
            "spin_strength": input.spin_strength(),
            "pan": input.pan(),
            "tilt": input.tilt(),
            "feeder_active": input.feeder_active(),
            "feed_interval": input.feed_interval(),
            "shaker_tuning": input.shaker_tuning(),
        }
        save_current_settings(settings)

# Create the Shiny app
app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app('web_magnus:app', reload=True, host="10.0.0.168", port=80)





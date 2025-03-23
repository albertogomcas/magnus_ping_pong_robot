from datetime import datetime
from shiny import App, ui, reactive, render
import requests
import json
import os
import matplotlib.pyplot as plt


# Robot URL
robot_url = "http://10.0.0.47"
PRESET_FILE = "presets.json"



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
                     ui.output_ui("status_ui"),
                     ),
        ui.nav_panel("Control",  # Second tab
                     ui.input_switch("launcher_active", "Launcher Active", False),
                     ui.input_action_button("feed_one", "Feed One Ball"),
                     ui.input_switch("feeder_active", "Continuous Feed", False),
                     ui.input_slider("speed", "Speed", min=0, max=100, value=0),
                     ui.input_slider("spin_angle", "Spin Angle", min=-180, max=180, value=0, step=10),
                     ui.input_slider("spin_strength", "Spin Strength", min=0, max=100, value=0, step=10),
                     ui.input_slider("pan", "Launcher Pan", min=-20, max=20, value=0, step=1),
                     ui.input_slider("tilt", "Launcher Tilt", min=-20, max=35, value=0, step=1),
                     ui.input_slider("feed_interval", "Ball Feed Interval (s)", min=1, max=10, value=5, step=0.5),
                     ui.input_action_button("save_preset", "Save Preset"),
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
        title=ui.output_text("status_navbar_ui"),
    )
)


# Shiny server logic
def server(input, output, session):
    session.robot_status_text = reactive.value("Status (🔴 Offline)")
    session.preset_list = reactive.value([])
    session.selected_preset = reactive.value("")
    session.preset_summary = reactive.value("No preset loaded")

    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        reactive.invalidate_later(1) # refresh every 1 second
        #status = robot_status()
        status = {"online": False}
        print(status)
        if status["online"]:
            session.robot_status_text.set("Status (🟢 Online)")
            return ui.div(
                ui.p(f"{datetime.now().strftime('%H:%M:%S')} Robot is online!"),

            )
        else:
            session.robot_status_text.set("Status (🔴 Offline)")
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
            feed_interval=input.feed_interval()
        )
        print(response)  # Output response for debugging
        return ui.notification_show("Settings sent to RoboPong!", type="success")

    # Handle the "Feed One" button press
    @reactive.Effect
    def feed_one():
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
        ui.notification_show("Preset saved!", type="success")
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

# Create the Shiny app
app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app('web_robopong:app', reload=True, host="10.0.0.168", port=80)





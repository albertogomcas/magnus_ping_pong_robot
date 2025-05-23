from shiny import App, ui, reactive, render, session
from datetime import datetime

# Import panel modules
from common import app_styles, save_current_settings, load_current_settings
from control_panel import ui_control, server_control
from presets_panel import ui_presets, server_presets
from target_panel import ui_target, server_target
from drill_panel import ui_drill, server_drill
from calibrate_panel import ui_calibrate, server_calibrate
from dev_panel import ui_dev, server_dev

# Initialize reactive values
current_sequence_index = reactive.Value(0)
sequence_running = reactive.Value(False)

# Shiny UI layout
app_ui = ui.page_fluid(
    ui.h2("Magnus WebUI"),
    app_styles,
    ui.page_navbar(
        ui_control(),
        ui_presets(),
        ui_target(),
        ui_drill(),
        ui_calibrate(),
        ui_dev(),
        title=ui.output_text("status_navbar_ui"),
        id="main_tab",
    )
)

# Shiny server logic
def server(input, output, session):
    # Initialize session variables
    session.robot_status_text = reactive.value("🔴 Offline")
    session.preset_list = reactive.value([])
    session.selected_preset = reactive.value("")
    session.preset_summary = reactive.value("No preset loaded")
    session.current_preset_name = reactive.value("")
    first_run = True

    # Register server functions from each panel
    server_control(input, output, session)
    server_presets(input, output, session)
    server_target(input, output, session)
    server_drill(input, output, session)
    server_calibrate(input, output, session)
    server_dev(input, output, session)

    # Display current preset
    @output
    @render.text
    def status_navbar_ui():
        return session.robot_status_text()

    # Load settings on startup
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
    run_app('app:app', reload=True, host="10.0.0.168", port=80)

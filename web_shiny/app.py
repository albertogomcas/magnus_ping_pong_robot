from shiny import App, ui, reactive, render, session

# Import panel modules
from common import app_styles, robot_status
from control_panel import ui_control, server_control
from presets_panel import ui_presets, server_presets
from target_panel import ui_target, server_target
from drill_panel import ui_drill, server_drill
from calibrate_panel import ui_calibrate, server_calibrate
from dev_panel import ui_dev, server_dev


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

# Create the Shiny app
app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app('app:app', reload=True, host="0.0.0.0", port=80)

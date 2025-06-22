from shiny import ui, reactive, render, App
from common import load_presets_from_file, sync_settings, set_sequence, start_sequence, stop_sequence
import concurrent.futures

# UI for the Drill panel
def ui_drill():
    return ui.nav_panel(
        "Drill",
        ui.h3("Drill Runner"),
        ui.p("Select multiple presets to run in sequence:"),
        ui.output_ui("drill_presets_ui"),
        ui.input_slider("drill_feed_interval", "Ball Feed Interval (s)", min=1, max=5, value=1, step=0.25),
        ui.input_switch("randomize_order", "Randomize preset order", value=False),
        ui.input_slider("repetitions", "Number of repetitions", min=1, max=20, value=1, step=1),
        ui.input_task_button("btn_start_drill", "Start Drill"),
        ui.input_action_button("btn_cancel_drill", "Cancel Drill", class_="btn-danger"),
    )

# Server logic for the Drill panel
def server_drill(input, output, session):
    log_lines = reactive.Value([])

    # Create UI for selecting multiple presets
    @output
    @render.ui
    def drill_presets_ui():
        presets = load_presets_from_file()
        if not presets:
            return ui.p("No presets available. Create some presets first.")

        # Create selectize input for multiple preset selection with repetitions
        return ui.div(
            ui.input_select(
                "selected_presets",
                "Select presets for drill:",
                choices=list(presets.keys()),
                multiple=True,
                selectize=True
            )
        )

    # Define the drill task
    @reactive.effect
    @reactive.event(input.btn_start_drill)
    def run_drill() -> None:
        presets = load_presets_from_file()
        selected_preset_names = list(input.selected_presets())
        selected_presets = [presets[name] for name in selected_preset_names]
        response = set_sequence(selected_presets)
        response = start_sequence(settings={"feed_interval":input.drill_feed_interval(), "randomize_order":input.randomize_order()})

    # Cancel the drill if the user presses "Cancel"
    @reactive.effect
    @reactive.event(input.btn_cancel_drill)
    def _cancel_drill():
        stop_sequence()
        # Turn off the feeder and launcher when canceled
        try:
            sync_settings(
                feeder_active=False,
                launcher_active=False,
                speed=0,
                spin_angle=0,
                spin_strength=0,
                pan=0,
                tilt=0,
                feed_interval=input.drill_feed_interval(),
            )
            ui.notification_show("Drill cancelled. Feeder and launcher turned off.", type="warning")
        except Exception as e:
            ui.notification_show(f"Error turning off feeder and launcher: {e}", type="error")


drill_app = App(ui.page_navbar(ui_drill()), server_drill)

if __name__ == "__main__":
    from shiny import run_app

    run_app("drill_panel:drill_app", reload=True, host="10.0.0.168", port=80)

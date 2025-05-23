from shiny import ui, reactive, render
import asyncio
import random
from common import load_presets_from_file, sync_settings


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
        ui.hr(),
        ui.output_text("drill_log"),
        ui.output_text_verbatim("drill_result")
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
    @ui.bind_task_button(button_id="btn_start_drill")
    @reactive.extended_task
    async def run_drill() -> None:
        print("Running drill")
        log_lines.set([])
        """Run the selected presets in sequence with the specified time gap."""
        drill_feed_interval = float(input.drill_feed_interval())
        selected_presets = input.selected_presets()
        if not selected_presets:
            return "No presets selected. Please select at least one preset."

        # Get number of repetitions
        repetitions = input.repetitions()

        # Check if randomize order is enabled
        randomize_order = input.randomize_order()

        presets = load_presets_from_file()
        lines = []

        # Calculate total number of presets to run (including repetitions)
        total_presets = len(selected_presets) * repetitions

        with ui.Progress(min=0, max=total_presets) as p:
            preset_counter = 0

            for rep in range(repetitions):
                # Create a copy of the selected presets for this repetition
                rep_presets = list(selected_presets)

                # Randomize order if enabled
                if randomize_order:
                    random.shuffle(rep_presets)
                    with reactive.lock():
                        log_lines.set(log_lines() + [f"Repetition {rep+1}/{repetitions}: Randomized order: {', '.join(rep_presets)}"])
                else:
                    with reactive.lock():
                        log_lines.set(log_lines() + [f"Repetition {rep+1}/{repetitions}: Keeping original order"])


                for preset_name in rep_presets:
                    if preset_name not in presets:
                        with reactive.lock():
                            log_lines.set(log_lines() + [f"Preset '{preset_name}' not found, skipping."])
                        preset_counter += 1
                        continue

                    preset = presets[preset_name]
                    with reactive.lock():
                        log_lines.set(log_lines() + [f"Running preset: {preset_name}"])

                    # Update progress
                    p.set(preset_counter, message=f"Running preset {preset_counter+1}/{total_presets}: {preset_name} (Rep {rep+1}/{repetitions})")

                    # Send preset settings to robot
                    try:
                        response = sync_settings(
                            feeder_active=True,
                            launcher_active=True,
                            speed=preset["speed"],
                            spin_angle=preset["spin_angle"],
                            spin_strength=preset["spin_strength"],
                            pan=preset["pan"],
                            tilt=preset["tilt"],
                            feed_interval=drill_feed_interval,
                            shaker=0  # Default value
                        )
                        with reactive.lock():
                            log_lines.set(log_lines() + [f"  Settings sent: {preset}"])
                    except Exception as e:
                        with reactive.lock():
                            log_lines.set(log_lines() + [f"  Error sending settings: {e}"])

                    # Wait for the specified time gap
                    await asyncio.sleep(drill_feed_interval)

                    # Increment preset counter
                    preset_counter += 1

        # Turn off the feeder and launcher when done
        try:
            response = sync_settings(
                feeder_active=False,
                launcher_active=False,
                speed=0,
                spin_angle=0,
                spin_strength=0,
                pan=0,
                tilt=0,
                feed_interval=drill_feed_interval,
                shaker=0
            )
            with reactive.lock():
                log_lines.set(log_lines() + ["✅ Drill complete"])
        except Exception as e:
            with reactive.lock():
                log_lines.set(log_lines() + ["Error turning off launcher and feeder"])




    # Cancel the drill if the user presses "Cancel"
    @reactive.effect
    @reactive.event(input.btn_cancel_drill)
    def _cancel_drill():
        run_drill.cancel()
        # Turn off the feeder and launcher when cancelled
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
                shaker=0
            )
            ui.notification_show("Drill cancelled. Feeder and launcher turned off.", type="warning")
        except Exception as e:
            ui.notification_show(f"Error turning off feeder and launcher: {e}", type="error")

    @output
    @render.text
    def drill_status():
        return f"Drill status: {run_drill.status()}"

    @output
    @render.text
    def drill_log():
        return "\n".join(log_lines()) or "(no output yet)"

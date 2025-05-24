from shiny import ui, reactive, render, App
import asyncio
from common import load_presets_from_file, sync_settings
import concurrent.futures
import time
import random
pool = concurrent.futures.ThreadPoolExecutor()


class DrillRunner:
    cancel = False

    @classmethod
    def sync_run_drill(cls, drill_feed_interval, selected_presets, repetitions, randomize_order=False) -> None:
        """Run the selected presets in sequence with the specified time gap."""
        if not selected_presets:
            return "No presets selected. Please select at least one preset."

        presets = load_presets_from_file()
        # Calculate total number of presets to run (including repetitions)
        total_presets = len(selected_presets) * repetitions


        preset_counter = 0

        for rep in range(repetitions):
            if cls.cancel:
                break
            # Create a copy of the selected presets for this repetition
            rep_presets = list(selected_presets)

            # Randomize order if enabled
            if randomize_order:
                random.shuffle(rep_presets)
                print(f"Repetition {rep+1}/{repetitions}: Randomized order: {', '.join(rep_presets)}")
            else:
                print(f"Repetition {rep+1}/{repetitions}: Keeping original order")


            for preset_name in rep_presets:
                if preset_name not in presets:
                    print(f"Preset '{preset_name}' not found, skipping.")
                    preset_counter += 1
                    continue

                preset = presets[preset_name]
                print(f"Running preset: {preset_name}")

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
                    print(f"  Settings sent: {preset}")
                except Exception as e:
                    print(f"  Error sending settings: {e}")

                # Wait for the specified time gap
                time.sleep(drill_feed_interval)

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
            print("✅ Drill complete")
        except Exception as e:
            print("Error turning off launcher and feeder")



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
        if DrillRunner.cancel:
            DrillRunner.cancel = False
        loop = asyncio.get_event_loop()
        loop.run_in_executor(pool, DrillRunner.sync_run_drill, input.drill_feed_interval(), input.selected_presets(), input.repetitions(), input.randomize_order())


    # Cancel the drill if the user presses "Cancel"
    @reactive.effect
    @reactive.event(input.btn_cancel_drill)
    def _cancel_drill():
        DrillRunner.cancel = True
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


drill_app = App(ui.page_navbar(ui_drill()), server_drill)

if __name__ == "__main__":
    from shiny import run_app

    run_app("drill_panel:drill_app", reload=True, host="10.0.0.168", port=80)

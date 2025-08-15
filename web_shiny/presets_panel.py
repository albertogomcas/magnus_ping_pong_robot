from shiny import ui, reactive, render
from common import save_preset_to_file, load_presets_from_file

# UI for the Presets panel
def ui_presets():
    return ui.nav_panel("Presets",
                ui.output_ui("preset_dropdown_ui"),
                ui.output_ui("preset_ui"),
                ui.input_action_button("delete_preset", "Delete Preset"),
            )

# Server logic for the Presets panel
def server_presets(input, output, session):
    # Display preset information
    @output()
    @render.ui
    def preset_ui():
        return ui.p(session.preset_summary())

    # Create dropdown for preset selection
    @output()
    @render.ui
    def preset_dropdown_ui():
        return ui.input_select("preset_dropdown", "Select Preset", choices=session.preset_list())

    # Handle preset loading
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

    @reactive.effect
    @reactive.event(input.delete_preset)
    def handle_delete_preset():
        preset_name = input.preset_dropdown()
        if preset_name:
            delete_preset_from_file(preset_name)
            session.preset_list.set(list(load_presets_from_file().keys()))
            session.preset_summary.set(f"Deleted Preset: {preset_name}")
            ui.notification_show("Preset deleted!", type="warning", duration=0.25)

    # Load presets on startup
    @reactive.Effect
    def load_presets_on_startup():
        session.preset_list.set(list(load_presets_from_file().keys()))

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

    # Handle the OK button in the save preset modal
    @reactive.effect
    @reactive.event(input.ok_preset_name)
    def handle_ok_preset():
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
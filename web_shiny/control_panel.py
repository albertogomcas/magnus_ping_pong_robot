from shiny import ui, reactive, render
from common import robot_status, sync_settings
from datetime import datetime

# UI for the Control panel
def ui_control():
    return ui.nav_panel("Control",
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
            )

# Server logic for the Control panel
def server_control(input, output, session):
    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        reactive.invalidate_later(1)  # refresh every 1 second
        status = robot_status()
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
            session.robot_status_text.set("🔴 Offline")
            return ui.p(f"{datetime.now().strftime('%H:%M:%S')} RoboPong is offline")

    @reactive.effect
    def sync_sliders():
        reactive.invalidate_later(2)  # poll every 2 s
        if getattr(session, "pause_sync_until", 0) > datetime.now().timestamp():
            return  # skip syncing for now
        status = robot_status()
        if status["online"]:
            status = status["result"]
            ui.update_switch("launcher_active", value=status["launcher"]["active"])
            ui.update_slider("speed", value=status["launcher"]["speed"])
            ui.update_slider("spin_angle", value=status["launcher"]["spin_angle"])
            ui.update_slider("spin_strength", value=status["launcher"]["spin_strength"])
            ui.update_slider("pan", value=status["aim"]["pan"])
            ui.update_slider("tilt", value=status["aim"]["tilt"])
            ui.update_switch("feeder_active", value=status["feeder"]["active"])
            ui.update_slider("feed_interval", value=status["feeder"]["interval"])

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
        )
        session.pause_sync_until = datetime.now().timestamp() + 2
        return ui.notification_show("Settings sent to RoboPong!", type="success", duration=0.25)
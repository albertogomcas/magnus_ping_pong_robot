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
                ui.input_slider("feed_interval", "Ball Feed Interval (s)", min=1, max=4, value=2, step=0.5),
            )

# Server logic for the Control panel
def server_control(input, output, session):
    robot_status_cache = reactive.value({"online": False, "result": {}})
    sliders_initialized = reactive.value(False)
    sync_in_progress = reactive.value(False)
    user_initiated_change = reactive.value(False)
    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        status = robot_status_cache()
        print("Refreshing status UI")
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
    def poll_robot_status():
        print("Polling robot status")
        print(f"sliders_initialized={sliders_initialized()}, sync_in_progress={sync_in_progress()}")
        reactive.invalidate_later(1)  # poll every 1 second

        try:
            new_status = robot_status()
            if "result" in new_status:
                if "detector" in new_status["result"]:
                    new_status["result"].pop("detector") # this always changes so we ignore it
            if new_status != robot_status_cache():
                print("New status: {}".format(new_status))
                print("old status: {}".format(robot_status_cache()))
                robot_status_cache.set(new_status)
        except Exception as e:
            print(f"Error polling robot status: {e}")
            # Don't update cache on error to avoid disrupting the UI

    @reactive.effect
    def sync_sliders():
        status = robot_status_cache()
        if status["online"]:
            if sync_in_progress():
                print("Sync in progress, skipping slider update")
                return

            try:
                sync_in_progress.set(True)
                user_initiated_change.set(False)  # Prevent triggering user handlers

                print("Updating sliders with new status")
                status_result = status["result"]
                ui.update_switch("launcher_active", value=status_result["launcher"]["active"])
                ui.update_slider("speed", value=status_result["launcher"]["speed"])
                ui.update_slider("spin_angle", value=status_result["launcher"]["spin_angle"])
                ui.update_slider("spin_strength", value=status_result["launcher"]["spin_strength"])
                ui.update_slider("pan", value=status_result["aim"]["pan"])
                ui.update_slider("tilt", value=status_result["aim"]["tilt"])
                ui.update_switch("feeder_active", value=status_result["feeder"]["active"])
                ui.update_slider("feed_interval", value=status_result["feeder"]["interval"])

                sliders_initialized.set(True)
            except Exception as e:
                print(f"Error updating sliders: {e}")
            finally:
                sync_in_progress.set(False)
                # Small delay before allowing user changes to be processed
                reactive.invalidate_later(0.1)


    # --- Guarded user-triggered settings sync ---
    # Create properly registered reactive effects for user input changes
    @reactive.effect
    def _on_feeder_active():
        input.feeder_active()  # Create dependency
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("feeder_active")

    @reactive.effect
    def _on_launcher_active():
        input.launcher_active()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("launcher_active")

    @reactive.effect
    def _on_speed():
        input.speed()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("speed")

    @reactive.effect
    def _on_spin_angle():
        input.spin_angle()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("spin_angle")

    @reactive.effect
    def _on_spin_strength():
        input.spin_strength()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("spin_strength")

    @reactive.effect
    def _on_pan():
        input.pan()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("pan")

    @reactive.effect
    def _on_tilt():
        input.tilt()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("tilt")

    @reactive.effect
    def _on_feed_interval():
        input.feed_interval()
        if not sliders_initialized() or sync_in_progress():
            return
        _send_current_settings("feed_interval")

    def _send_current_settings(changed_input):
        """Helper to send settings when user changes an input"""
        try:
            new_settings = dict(
                feeder_active=input.feeder_active(),
                launcher_active=input.launcher_active(),
                speed=input.speed(),
                spin_angle=input.spin_angle(),
                spin_strength=input.spin_strength(),
                pan=input.pan(),
                tilt=input.tilt(),
                feed_interval=input.feed_interval(),
            )
            print(f"User changed {changed_input}, sending settings: {new_settings}")
            response = sync_settings(**new_settings)
            ui.notification_show("Settings sent to RoboPong!", type="message", duration=0.25)
        except Exception as e:
            print(f"Error sending settings: {e}")
            ui.notification_show(f"Error: {e}", type="error", duration=2)

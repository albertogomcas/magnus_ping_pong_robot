from shiny import ui, reactive, render
from common import (
    robot_status,
    set_speed, set_spin, set_aim, set_feed_interval,
    activate, halt,
    sync_settings,
)
from datetime import datetime

# UI for the Control panel
def ui_control():
    return ui.nav_panel("Control",
                ui.output_ui("status_ui"),
                ui.input_switch("active", "Active (Launcher + Feeder)", False),
                ui.input_slider("feed_interval", "Ball Feed Interval (s)", min=1, max=4, value=2, step=0.5),
                ui.hr(),
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
            )

# Server logic for the Control panel
def server_control(input, output, session):
    robot_status_cache = reactive.value({"online": False, "result": {}})
    # True once we have loaded robot state into sliders for the first time.
    # After that sliders are the source of truth — polling never touches them.
    sliders_initialized = reactive.value(False)

    # Render status UI based on robot connection status
    @output()
    @render.ui
    def status_ui():
        status = robot_status_cache()
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
        reactive.invalidate_later(2)  # poll every 2s — only for online/supply indicator

        try:
            new_status = robot_status()
            if "result" in new_status:
                if "detector" in new_status["result"]:
                    new_status["result"].pop("detector")  # always changes, ignore it
            if new_status != robot_status_cache():
                robot_status_cache.set(new_status)
        except Exception as e:
            print(f"Error polling robot status: {e}")

    @reactive.effect
    def init_sliders_once():
        """Push robot state into sliders exactly once, on first successful poll."""
        status = robot_status_cache()
        if sliders_initialized() or not status["online"]:
            return

        try:
            r = status["result"]
            is_active = r["launcher"]["active"] and r["feeder"]["active"]
            ui.update_switch("active", value=is_active)
            ui.update_slider("speed",          value=r["launcher"]["speed"])
            ui.update_slider("spin_angle",     value=r["launcher"]["spin_angle"])
            ui.update_slider("spin_strength",  value=r["launcher"]["spin_strength"])
            ui.update_slider("pan",            value=r["aim"]["pan"])
            ui.update_slider("tilt",           value=r["aim"]["tilt"])
            ui.update_slider("feed_interval",  value=r["feeder"]["interval"])
            sliders_initialized.set(True)
            print("[control_panel] Sliders initialised from robot state")
        except Exception as e:
            print(f"[control_panel] Error initialising sliders: {e}")

    # ------------------------------------------------------------------ #
    #  Input handlers — each calls only its own RPC, no full-state reads  #
    # ------------------------------------------------------------------ #

    @reactive.effect
    def _on_active():
        is_active = input.active()
        if not sliders_initialized():
            return
        try:
            if is_active:
                activate()
            else:
                halt()
            ui.notification_show("✓", type="message", duration=0.5)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

    @reactive.effect
    def _on_speed():
        speed = input.speed()
        if not sliders_initialized():
            return
        try:
            set_speed(speed)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

    @reactive.effect
    def _on_spin():
        # Both spin sliders batched together — only fires when either changes
        angle    = input.spin_angle()
        strength = input.spin_strength()
        if not sliders_initialized():
            return
        try:
            set_spin(angle, strength)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

    @reactive.effect
    def _on_pan():
        pan = input.pan()
        if not sliders_initialized():
            return
        try:
            set_aim(pan=pan)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

    @reactive.effect
    def _on_tilt():
        tilt = input.tilt()
        if not sliders_initialized():
            return
        try:
            set_aim(tilt=tilt)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

    @reactive.effect
    def _on_feed_interval():
        interval = input.feed_interval()
        if not sliders_initialized():
            return
        try:
            set_feed_interval(interval)
        except Exception as e:
            ui.notification_show(f"Error: {e}", type="error", duration=2)

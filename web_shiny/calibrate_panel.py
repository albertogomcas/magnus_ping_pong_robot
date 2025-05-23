from shiny import ui, reactive
import requests
from common import robot_url

# UI for the Calibrate panel
def ui_calibrate():
    return ui.nav_panel(
        "Calibrate",
        ui.input_action_button("calibrate_btn", "Calibrate Aim Zero"),
    )

# Server logic for the Calibrate panel
def server_calibrate(input, output, session):
    @reactive.effect
    @reactive.event(input.calibrate_btn)
    def calibrate_aim_zero():
        url = robot_url + "/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "calibrate_aim_zero",
            "id": 4,
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
            result = response.json()
            print(result)
            ui.notification_show("Calibration command sent!", type="success", duration=1)
        except Exception as e:
            print(f"Calibration failed: {e}")
            ui.notification_show("Calibration failed.", type="error", duration=1)
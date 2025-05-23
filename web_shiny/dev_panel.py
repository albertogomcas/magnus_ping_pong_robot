from shiny import ui, reactive
import requests
from common import robot_url

# UI for the Dev panel
def ui_dev():
    return ui.nav_panel(
        "Dev",
        ui.input_action_button("reset", "Reset ESP32"),
        ui.input_action_button("enable_simulation", "Enable simulation mode"),
        ui.input_action_button("disable_simulation", "Disable simulation mode"),
        ui.input_action_button("interrupt_server", "Interrupt jRPC server"),
    )

# Helper function to send JSON-RPC commands
def send_jsonrpc_command(method, id=1):
    """
    Send a JSON-RPC command to the robot and handle the response.

    Args:
        method (str): The JSON-RPC method to call
        id (int): The JSON-RPC request ID

    Returns:
        dict or None: The JSON response if successful, None otherwise
    """
    # Construct appropriate success and error messages based on the method name
    method_readable = method.replace("_", " ")
    success_msg = f"{method_readable.capitalize()} command sent!"
    error_msg = f"{method_readable.capitalize()} command failed"
    url = robot_url + "/rpc"
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": id,
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False, timeout=1)
        result = response.json()
        print(result)
        ui.notification_show(success_msg, type="success", duration=1)
        return result
    except Exception as e:
        error_detail = f"{error_msg}: {e}"
        print(error_detail)
        ui.notification_show(error_msg, type="error", duration=1)
        return None

# Server logic for the Dev panel
def server_dev(input, output, session):
    @reactive.Effect
    @reactive.event(input.reset)
    def reset():
        send_jsonrpc_command(
            method="reset",
            id=5
        )

    @reactive.Effect
    @reactive.event(input.interrupt_server)
    def interrupt_server():
        send_jsonrpc_command(
            method="interrupt",
            id=5
        )

    @reactive.Effect
    @reactive.event(input.enable_simulation)
    def enable_simulation():
        send_jsonrpc_command(
            method="enable_simulation",
            id=7
        )

    @reactive.Effect
    @reactive.event(input.disable_simulation)
    def disable_simulation():
        send_jsonrpc_command(
            method="disable_simulation",
            id=9
        )

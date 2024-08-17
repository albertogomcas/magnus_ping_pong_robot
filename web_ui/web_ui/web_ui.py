"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
import requests
import json

from rxconfig import config

robot_url = "http://10.0.0.47"

#describe the parameters of the robot
params = {
   "active": ["bool", None, False],
   "spin_angle": ["int", (-180, 180), 0],
   "spin_strength": ["int", (0, 100), 0],
   "pan": ["float", (-20, 20), 0],
   "tilt": ["float", (-10, 10), 0],
   "feed_rate": ["float", (0, 1)],
}


class State(rx.State):
    """The app state."""
    active: bool = False
    spin_angle: int = 0
    spin_strength: int = 10
    pan: float = 0
    tilt: float = 0
    feed_rate: float = 0

    def sync_settings(self):
        print(self)

    def set_spin_angle(self, value):
        self.spin_angle = value

    def set_spin_strength(self, value):
        self.spin_strength = value

    def set_pan(self, value):
        self.pan = value

    def set_tilt(self, value):
        self.tilt = value

    def set_feed_rate(self, value):
        self.feed_rate = value



class ArduinoState(rx.State):
    form_data: dict = {}

    def send_command(self, data):
        print(data)
        self.form_data = data

        if not data['arduino']:
            return

        url = robot_url + "/rpc"

        payload = {
        "jsonrpc": "2.0",
        "method": "arduino",
        "params": ["<" + data['arduino'] + ">"],
        "id": 1,
        }
        headers = {'Content-Type': 'application/json'}

        print(payload)

        response = requests.post(url, headers=headers, json=payload, verify=False)
        print(response.json())

def slider(name, state, text="", min=0, max=100, step=1):
    text = text or name

    return rx.container(
    rx.vstack(
        rx.hstack(
            rx.text(text),
            rx.text(getattr(state, name)),
        ),
        rx.slider(name=name, min=min, max=max, step=step, on_value_commit=getattr(state, f"set_{name}"), default_value=getattr(state, name),
    ),
    ),
    )

def index() -> rx.Component:
    return rx.container(
        rx.vstack(
        rx.heading("RoboPong WebUI"),
        rx.divider(),
        rx.hstack(
        rx.card(
            rx.heading("Control"),
        rx.flex(
            rx.switch(default_checked=False),
            rx.text("Active"),
            spacing="4",
        ),
        slider("spin_angle", State, "Spin Angle", min=-180, max=180, step=15),
        slider("spin_strength", State, "Spin Strength", min=0, max=100, step=10),
        slider("pan", State, "Launcher pan", min=-10, max=10, step=1),
        slider("tilt", State, "Launcher tilt", min=-10, max=10, step=1),
        slider("feed_rate", State, "Ball feed rate", min=0, max=2, step=0.1),

        rx.spacer(),
        rx.button("Send settings", on_click=State.sync_settings),
        spacing="4",
        ),
         rx.card(
             rx.form.root(
                 rx.vstack(
                     rx.heading("Arduino sender"),
                     rx.input(name="arduino", placeholder="Enter command...", type="text"),
                     rx.button("Send", type="submit"),
                 ),
             on_submit=ArduinoState.send_command,
             reset_on_submit=False,
             width="100%",
         ),
        ),
        ),
        ),
    )



app = rx.App()
app.add_page(index)

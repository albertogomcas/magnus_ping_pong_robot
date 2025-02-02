"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx
import requests
import json

from rxconfig import config

robot_url = "http://10.0.0.47"

#describe the parameters of the robot
params = {
   "active": ["bool", None, False],
   "speed": ["int", (0, 100), 0],
   "spin_angle": ["int", (-180, 180), 0],
   "spin_strength": ["int", (0, 100), 0],
   "pan": ["float", (-20, 20), 0],
   "tilt": ["float", (-10, 10), 0],
   "feed_interval": ["int", (1, 10)],
}

class Preset(rx.Base):
    """The launcher preset model."""
    speed: int
    spin_angle: int
    spin_strength: int
    pan: float
    tilt: float

class PresetsManager(rx.State):
    presets: list[Preset] = [
        Preset(speed=30, spin_angle=0, spin_strength=0, pan=0, tilt=10),
        Preset(speed=60, spin_angle=90, spin_strength=50, pan=0, tilt=10),
    ]

    def add_preset(self, data:dict):
        self.presets.append(Preset(**data))
        self.transform_data()

    def transform_data(self):
        print(self.presets)



class State(rx.State):
    """The current state."""
    active: bool = False
    speed: int = 0
    spin_angle: int = 0
    spin_strength: int = 10
    pan: float = 0
    tilt: float = 0
    feed_interval: int = 5

    def sync_settings(self):
        url = robot_url + "/rpc"

        payload = {
            "jsonrpc": "2.0",
            "method": "sync_settings",
            "params": {"settings" : dict(
                active=self.active,
                speed=self.speed,
                spin_angle=self.spin_angle,
                spin_strength=self.spin_strength,
                pan=self.pan,
                tilt=self.tilt,
                feed_interval=self.feed_interval,
            ),
            },
            "id": 1,
        }
        headers = {'Content-Type': 'application/json'}

        print(payload)

        response = requests.post(url, headers=headers, json=payload, verify=False)
        print(response)

    def set_speed(self, value:int):
        self.speed = value[0]

    def set_spin_angle(self, value:int):
        self.spin_angle = value[0]

    def set_spin_strength(self, value:int):
        self.spin_strength = value[0]

    def set_pan(self, value:float):
        self.pan = value[0]

    def set_tilt(self, value:float):
        self.tilt = value[0]

    def set_feed_interval(self, value:int):
        self.feed_interval = value[0]

    def set_active(self, value:bool):
        self.active = value

    def save_preset(self):
        preset = dict(
            speed=self.speed,
            spin_strength=self.spin_strength,
            spin_angle=self.spin_angle,
            tilt=self.tilt,
            pan=self.pan,
        )
        print(preset)

        self.get_state(PresetsManager).add_preset(preset)


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

def show_preset(preset:Preset):
    return rx.table.row(
        rx.table.cell(f"{preset.speed}"),
        rx.table.cell(f"{preset.spin_strength}% {preset.spin_angle}"),
        rx.table.cell(f"T{preset.tilt} P{preset.pan}"),
        style={"_hover":
                    {"bg": rx.color("gray", 3)}
              },
    align = "center",
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
                rx.switch(default_checked=False, on_change=State.set_active),
                rx.text("Active"),
                spacing="4",
            ),
            slider("speed", State, "Speed", min=0, max=100, step=1),
            slider("spin_angle", State, "Spin Angle", min=-180, max=180, step=15),
            slider("spin_strength", State, "Spin Strength", min=0, max=100, step=10),
            slider("pan", State, "Launcher pan", min=-10, max=10, step=1),
            slider("tilt", State, "Launcher tilt", min=-10, max=25, step=1),
            slider("feed_interval", State, "Ball feed interval", min=1, max=10, step=1),

            rx.spacer(),
            rx.button("Send settings", on_click=State.sync_settings),
            spacing="4",
            ),
            rx.button("Save preset", on_click=State.save_preset),
            spacing="4",
        ),
            rx.card(
                rx.heading("Presets"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Speed"),
                            rx.table.column_header_cell("Spin"),
                            rx.table.column_header_cell("Aim"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            PresetsManager.presets, show_preset
                        ),
                    ),
                    variant="surface",
                    size="3",
                    width="100%",
                ),

            )
    ),
    )



app = rx.App()
app.add_page(index)

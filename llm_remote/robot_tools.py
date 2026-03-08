"""
robot_tools.py  –  OpenWebUI Tools for the RoboPong Magnus robot.

Drop this file into OpenWebUI → Tools.
The LLM will be able to call any of the methods below to control the robot.
"""

import json
import requests
from pydantic import Field

ROBOT_URL = "http://10.0.0.47"
_rpc_id = 0


def _rpc(method: str, params: dict | None = None, timeout: int = 3) -> str:
    """Send one JSON-RPC 2.0 request; return a plain-text result string."""
    global _rpc_id
    _rpc_id += 1
    payload = {"jsonrpc": "2.0", "method": method, "id": _rpc_id}
    if params:
        payload["params"] = params
    try:
        r = requests.post(
            ROBOT_URL + "/rpc",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=timeout,
        )
        body = r.json()
        if "error" in body:
            return f"Error: {body['error']}"
        result = body.get("result", {})
        return json.dumps(result)
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            return "Error: request timed out"
        return f"Error: {e}"


class Tools:
    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    #  General
    # ------------------------------------------------------------------ #

    def status(self) -> str:
        """
        Get the current robot status (launcher, feeder, aim, detector).
        """
        return _rpc("status")

    def activate(self) -> str:
        """
        Start the launcher and feeder. Balls will be launched continuously.
        """
        return _rpc("activate")

    def halt(self) -> str:
        """
        Stop the launcher and feeder immediately.
        """
        return _rpc("halt")

    def feed_one(self) -> str:
        """
        Feed a single ball without changing any other setting.
        """
        return _rpc("feed_one")

    # ------------------------------------------------------------------ #
    #  Aim
    # ------------------------------------------------------------------ #

    def aim_up(self, step: int = Field(1, description="Degrees to tilt up (1-10).")) -> str:
        """
        Tilt the launcher upward by step degrees.
        """
        return _rpc("aim_up", {"step": step})

    def aim_down(self, step: int = Field(1, description="Degrees to tilt down (1-10).")) -> str:
        """
        Tilt the launcher downward by step degrees.
        """
        return _rpc("aim_down", {"step": step})

    def aim_left(self, step: int = Field(1, description="Degrees to pan left (1-10).")) -> str:
        """
        Pan the launcher to the left by step degrees.
        """
        return _rpc("aim_left", {"step": step})

    def aim_right(self, step: int = Field(1, description="Degrees to pan right (1-10).")) -> str:
        """
        Pan the launcher to the right by step degrees.
        """
        return _rpc("aim_right", {"step": step})

    def aim_center(self) -> str:
        """
        Reset aim to the center position.
        """
        return _rpc("aim_center")

    def set_aim(
        self,
        tilt: float = Field(None, description="Absolute vertical angle in degrees. Omit to keep current."),
        pan: float = Field(None, description="Absolute horizontal angle in degrees. Omit to keep current."),
    ) -> str:
        """
        Set the aim to an absolute position. Omit either axis to leave it unchanged.
        """
        params = {}
        if tilt is not None:
            params["tilt"] = tilt
        if pan is not None:
            params["pan"] = pan
        return _rpc("set_aim", params)

    # ------------------------------------------------------------------ #
    #  Launcher speed
    # ------------------------------------------------------------------ #

    def set_speed(
        self,
        speed: int = Field(..., description="Launch speed 0-100."),
    ) -> str:
        """
        Set the launcher speed (0-100). Does not change spin or active state.
        """
        return _rpc("set_launcher", {"speed": speed})

    def speed_up(self, step: int = Field(2, description="Amount to increase speed by.")) -> str:
        """
        Increase launcher speed by step.
        """
        return _rpc("speed_up", {"step": step})

    def speed_down(self, step: int = Field(2, description="Amount to decrease speed by.")) -> str:
        """
        Decrease launcher speed by step.
        """
        return _rpc("speed_down", {"step": step})

    # ------------------------------------------------------------------ #
    #  Spin presets
    # ------------------------------------------------------------------ #

    def no_spin(self) -> str:
        """
        Remove all spin. Ball will be launched flat.
        """
        return _rpc("no_spin")

    def spin_random(self) -> str:
        """
        Apply a random spin direction and strength.
        """
        return _rpc("spin_random")

    def spin_topspin(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply topspin (ball dips toward the opponent).
        """
        return _rpc("spin_T", {"strength": strength})

    def spin_backspin(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply backspin (ball floats / bounces back).
        """
        return _rpc("spin_B", {"strength": strength})

    def spin_left(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply left sidespin (ball curves to the left).
        """
        return _rpc("spin_L", {"strength": strength})

    def spin_right(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply right sidespin (ball curves to the right).
        """
        return _rpc("spin_R", {"strength": strength})

    def spin_top_left(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply top-left diagonal spin.
        """
        return _rpc("spin_TL", {"strength": strength})

    def spin_top_right(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply top-right diagonal spin.
        """
        return _rpc("spin_TR", {"strength": strength})

    def spin_back_left(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply back-left diagonal spin.
        """
        return _rpc("spin_BL", {"strength": strength})

    def spin_back_right(
        self,
        strength: float = Field(0.5, description="Spin strength 0.0-1.0."),
    ) -> str:
        """
        Apply back-right diagonal spin.
        """
        return _rpc("spin_BR", {"strength": strength})

    def increase_spin(
        self,
        step: int = Field(10, description="Amount to increase spin strength by (0-100 scale)."),
    ) -> str:
        """
        Increase the current spin strength.
        """
        return _rpc("increase_spin", {"step": step})

    def decrease_spin(
        self,
        step: int = Field(10, description="Amount to decrease spin strength by (0-100 scale)."),
    ) -> str:
        """
        Decrease the current spin strength.
        """
        return _rpc("decrease_spin", {"step": step})

    # ------------------------------------------------------------------ #
    #  Feed interval
    # ------------------------------------------------------------------ #

    def set_feed_interval(
        self,
        interval: float = Field(..., description="Seconds between balls. Range: 0.5-10."),
    ) -> str:
        """
        Set how many seconds to wait between launching each ball.
        """
        return _rpc("set_feed_interval", {"interval": interval})

    def interval_up(
        self,
        step: float = Field(0.25, description="Seconds to add to the current interval."),
    ) -> str:
        """
        Increase the feed interval (slower ball rate).
        """
        return _rpc("interval_up", {"step": step})

    def interval_down(
        self,
        step: float = Field(0.25, description="Seconds to subtract from the current interval."),
    ) -> str:
        """
        Decrease the feed interval (faster ball rate).
        """
        return _rpc("interval_down", {"step": step})



import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def load_remote():
    root = Path(__file__).resolve().parents[2]
    path = root / "esp_app" / "remote_device" / "main.py"

    machine = ModuleType("machine")
    machine.Pin = MagicMock()
    machine.I2C = MagicMock()
    machine.ADC = MagicMock()
    keypad = ModuleType("keypad")
    keypad.Keypad = MagicMock()
    oled_display = ModuleType("oled_display")
    oled_display.OLEDDisplay = MagicMock()
    sender = ModuleType("espnow_sender")
    sender.ESPNowSender = MagicMock()

    spec = importlib.util.spec_from_file_location("test_remote_drill_modes", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "machine": machine,
        "keypad": keypad,
        "oled_display": oled_display,
        "espnow_sender": sender,
    }):
        spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "layer,key,press_type,expected_action",
    [
        (3, "2", "short", "apply_preset_2"),
        (3, "2", "long", "save_preset_2"),
        (4, "3", "short", "append_preset_3"),
        (4, "3", "long", "save_sequence_3"),
        (4, "0", "long", "clear_sequence_draft"),
        (5, "7", "long", "start_random_sequence_7"),
        (5, "0", "long", "toggle_sequence_loop"),
    ],
)
def test_drill_mode_key_actions(layer, key, press_type, expected_action):
    module = load_remote()
    remote = module.RemoteController.__new__(module.RemoteController)
    remote.current_layer = layer
    remote.layers = {layer: {key: "placeholder"}}
    remote.sender = MagicMock()
    remote.display = MagicMock()

    with patch.object(module.asyncio, "create_task", side_effect=lambda coroutine: coroutine.close()):
        remote.handle_key(key, press_type)

    sent_message = remote.sender.send.call_args.args[0]
    assert sent_message["action"] == expected_action
    assert sent_message["press_type"] == press_type


def test_robot_errors_show_once_until_changed_or_cleared():
    module = load_remote()
    remote = module.RemoteController.__new__(module.RemoteController)
    remote.status = {}
    remote.error_message = ""
    remote.last_robot_error = None
    remote.update_display = MagicMock()

    with patch.object(module.time, "ticks_ms", return_value=123, create=True):
        remote.handle_status({"e": "Vertical servo feedback failed", "n": 1, "t": None, "p": None})
        assert remote.error_message == "Vertical servo feedback failed"
        assert remote.status["tilt"] is None
        remote.error_message = ""
        remote.handle_status({"e": "Vertical servo feedback failed", "n": 1})
        assert remote.error_message == ""
        remote.handle_status({"e": "Vertical servo feedback failed", "n": 2})
        assert remote.error_message == "Vertical servo feedback failed"
        remote.handle_status({"e": "", "n": 2})
        remote.error_message = ""
        remote.handle_status({"e": "Vertical servo feedback failed", "n": 2})
        assert remote.error_message == "Vertical servo feedback failed"


def test_error_disappears_after_four_seconds():
    module = load_remote()
    remote = module.RemoteController.__new__(module.RemoteController)
    remote.error_message = ""
    remote.update_display = MagicMock()

    with patch.object(module.time, "ticks_ms", side_effect=[1000, 4999, 5000], create=True), \
         patch.object(module.time, "ticks_diff", side_effect=lambda a, b: a - b, create=True):
        remote.show_error("Cannot send to robot")
        remote.clear_expired_error()
        assert remote.error_message == "Cannot send to robot"
        remote.clear_expired_error()
        assert remote.error_message == ""
        assert remote.update_display.call_count == 2


def test_oled_shows_error_description_and_missing_aim():
    path = Path(__file__).resolve().parents[2] / "esp_app" / "remote_device" / "oled_display.py"
    spec = importlib.util.spec_from_file_location("test_oled_display", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"ssd1306": ModuleType("ssd1306")}):
        spec.loader.exec_module(module)
    display = module.OLEDDisplay.__new__(module.OLEDDisplay)
    display.oled = MagicMock()

    display.show_error("Horizontal servo: timeout")
    assert [call.args[0] for call in display.oled.text.call_args_list] == [
        "ROBOT ERROR", "Horizontal servo", ": timeout",
    ]
    display.oled.text.reset_mock()
    display._draw_aim_info({"tilt": None, "pan": None})
    assert [call.args[0] for call in display.oled.text.call_args_list] == [
        "Vert: --", "Horiz: --",
    ]

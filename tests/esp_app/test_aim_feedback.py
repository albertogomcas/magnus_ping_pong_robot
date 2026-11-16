import importlib.util
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def load_parts():
    path = Path(__file__).resolve().parents[2] / "esp_app" / "parts.py"
    machine = ModuleType("machine")
    for name in ("Pin", "PWM", "ADC", "UART"):
        setattr(machine, name, MagicMock())
    modules = {
        "machine": machine,
        "dev": SimpleNamespace(DevFlags=SimpleNamespace(simulation_mode=False)),
        "espnow": ModuleType("espnow"),
        "network": ModuleType("network"),
    }
    spec = importlib.util.spec_from_file_location("test_aim_parts", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("axis", ["vertical", "horizontal"])
def test_feedback_failure_is_identified_and_aim_step_is_rejected(axis):
    module = load_parts()
    vertical = MagicMock()
    horizontal = MagicMock()
    vertical.status.return_value = horizontal.status.return_value = {"angle": 180}
    (vertical if axis == "vertical" else horizontal).status.side_effect = OSError("timeout")
    aimer = module.Aimer(vertical, horizontal)

    with pytest.raises(RuntimeError, match=axis.capitalize() + " servo: timeout"):
        aimer.up()
    vertical.move.assert_not_called()
    horizontal.move.assert_not_called()


def test_servo_read_failure_is_counted_and_clears_the_bus():
    path = Path(__file__).resolve().parents[2] / "esp_app" / "stservo_wrapper.py"
    sts = ModuleType("stservo.sts")
    sts.sts = MagicMock()
    port = ModuleType("stservo.port_handler")
    port.PortHandler = MagicMock()
    constants = ModuleType("stservo.stservo_def")
    constants.COMM_SUCCESS = 0
    spec = importlib.util.spec_from_file_location("test_servo_wrapper", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"stservo.sts": sts, "stservo.port_handler": port,
                                  "stservo.stservo_def": constants}):
        spec.loader.exec_module(module)
    servo = module.STServo.__new__(module.STServo)
    servo.servo_id = 3
    servo.sts = MagicMock()
    servo.sts.ReadPosSpeed.return_value = (0, 0, -1, 0)
    servo.sts.getTxRxResult.return_value = "timeout"
    servo.ph = MagicMock()
    servo.comm_failures = 0
    servo.consecutive_failures = 0

    with pytest.raises(Exception, match="timeout"):
        servo.status()
    assert servo.comm_failures == 1
    servo.ph.clearPort.assert_called_once()


def test_aim_uses_faster_servo_speed():
    module = load_parts()
    vertical = MagicMock()
    horizontal = MagicMock()
    aimer = module.Aimer(vertical, horizontal)

    aimer.aim(10, -5)

    vertical.move.assert_called_once_with(140, 100)
    horizontal.move.assert_called_once_with(200, 100)


def test_detector_counts_pulses_with_millisecond_debounce(monkeypatch):
    module = load_parts()
    clock = [1000]
    monkeypatch.setattr(time, "ticks_ms", lambda: clock[0], raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b, raising=False)
    pin = MagicMock()
    monkeypatch.setattr(module, "Pin", MagicMock(return_value=pin, IN=1, PULL_DOWN=2, IRQ_RISING=4))
    detector = module.Detector(34)

    detector.handle_detection(pin)
    clock[0] += 100
    detector.handle_detection(pin)
    assert detector.status() == {"elapsed": 0.1, "count": 1}
    clock[0] += 50
    detector.handle_detection(pin)
    assert detector.status() == {"elapsed": 0.0, "count": 2}

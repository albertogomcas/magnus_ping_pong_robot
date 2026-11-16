import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def load_magnus():
    root = Path(__file__).resolve().parents[2]
    path = root / "esp_app" / "magnus.py"

    machine = ModuleType("machine")
    machine.Pin = MagicMock()
    machine.UART = MagicMock()

    microdot = ModuleType("microdot")
    microdot.Microdot = MagicMock()
    microdot.Response = MagicMock()

    parts = ModuleType("parts")
    for name in ("Feeder", "Launcher", "Aimer", "Shaker", "Detector", "Supply", "Remote", "ESPNowRemote"):
        setattr(parts, name, MagicMock())

    stservo_wrapper = ModuleType("stservo_wrapper")
    stservo_wrapper.STServo = MagicMock()
    stservo = ModuleType("stservo")
    stservo.__path__ = []
    port_handler = ModuleType("stservo.port_handler")
    port_handler.PortHandlerMicroPython = MagicMock()

    modules = {
        "machine": machine,
        "microdot": microdot,
        "parts": parts,
        "stservo_wrapper": stservo_wrapper,
        "stservo": stservo,
        "stservo.port_handler": port_handler,
        "dev": SimpleNamespace(DevFlags=SimpleNamespace(simulation_mode=False)),
    }
    spec = importlib.util.spec_from_file_location("esp_app._magnus_sequence_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.Magnus


@pytest.fixture
def magnus(monkeypatch):
    monkeypatch.setattr(time, "ticks_ms", lambda: int(time.monotonic() * 1000), raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b, raising=False)
    cls = load_magnus()
    instance = cls.__new__(cls)
    instance.sequence = [{}]
    instance.active_sequence = True
    instance._randomize_sequence = False
    instance._loop_sequence = False
    instance._sequence_idx = 0
    instance._sequence_order = [0]
    instance._sequence_generation = 1
    instance._sequence_task = None
    instance.launcher = MagicMock()
    instance.feeder = MagicMock()
    instance.detector = MagicMock()
    instance.detector.status.return_value = {"count": 0}
    instance.set_settings = MagicMock()
    instance.flush_servo_uart = MagicMock()
    instance.wait_detector = AsyncMock(return_value=True)
    return instance


def test_stopping_sequence_cancels_task_and_halts_both_motors(magnus):
    task = MagicMock()
    magnus._sequence_task = task

    magnus.stop_sequence()

    assert magnus.active_sequence is False
    assert magnus._sequence_task is None
    task.cancel.assert_called_once()
    magnus.launcher.halt.assert_called_once()
    magnus.feeder.halt.assert_called_once()


def test_sequence_stops_after_one_pass_when_loop_is_disabled(magnus):
    asyncio.run(magnus.run_sequence(1))

    assert magnus.active_sequence is False
    magnus.set_settings.assert_called_once_with(
        launcher_active=True,
        feeder_active=True,
    )
    magnus.launcher.halt.assert_called_once()
    magnus.feeder.halt.assert_called_once()


def test_cannot_start_empty_sequence(magnus):
    magnus.sequence = []
    magnus.active_sequence = False

    with pytest.raises(ValueError, match="empty sequence"):
        magnus.start_sequence()


def test_remote_status_fits_espnow_with_error_and_reports_missing_aim(magnus):
    magnus.launcher.status.return_value = {
        "active": True, "speed": 100, "spin_angle": -180, "spin_strength": 100,
    }
    magnus.feeder.status.return_value = {"interval": 10.0}
    magnus.aimer = MagicMock()
    magnus.aimer.status.side_effect = RuntimeError("Vertical servo feedback failed")
    magnus.remote = SimpleNamespace(last_error='x"\\' * 40, error_id=9999)
    magnus.sequence_draft = list(range(9))
    magnus.remote_message = 'x"\\' * 20

    status = magnus.remote_status()
    status["type"] = "status_response"

    assert status["t"] is None and status["p"] is None
    assert len(json.dumps(status).encode("utf-8")) <= 250
    assert len(status["e"]) == 48
    assert '"' not in status["e"] and "\\" not in status["e"]
    magnus.remote.last_error = ""
    assert magnus.remote_status()["e"] == "Vertical servo feedback failed"


def test_wait_advances_on_detector_pulse_even_if_it_arrived_during_settling(magnus):
    magnus.detector.status.return_value = {"count": 8}
    magnus.feeder.interval = 4
    wait = type(magnus).wait_detector(magnus, 1, 7, time.ticks_ms())
    assert asyncio.run(wait) is True


def test_wait_advances_only_after_current_feed_interval(magnus, monkeypatch):
    clock = [0]
    monkeypatch.setattr(time, "ticks_ms", lambda: clock[0])
    magnus.feeder.interval = 0.75
    waits = []

    async def advance(seconds):
        waits.append(seconds)
        clock[0] += round(seconds * 1000)

    with patch.object(asyncio, "sleep", side_effect=advance):
        result = asyncio.run(type(magnus).wait_detector(magnus, 1, 0, 0))

    assert result is True
    assert clock[0] == 750
    assert waits[-1] == pytest.approx(0.05)


def test_wait_observes_stop_before_advancing(magnus, monkeypatch):
    monkeypatch.setattr(time, "ticks_ms", lambda: 0)
    magnus.feeder.interval = 1

    async def stop(_):
        magnus.active_sequence = False

    with patch.object(asyncio, "sleep", side_effect=stop):
        result = asyncio.run(type(magnus).wait_detector(magnus, 1, 0, 0))

    assert result is False


def test_sequence_advances_on_pulse_then_timeout(magnus, monkeypatch):
    clock = [0]
    monkeypatch.setattr(time, "ticks_ms", lambda: clock[0])
    magnus.sequence = [{"speed": 10}, {"speed": 20}]
    magnus._sequence_order = [0, 1]
    magnus.feeder.interval = 1
    magnus.detector.status.side_effect = lambda: {"count": int(clock[0] >= 200)}
    del magnus.wait_detector
    applied = []
    magnus.set_settings.side_effect = lambda **settings: applied.append((clock[0], settings["speed"]))

    async def advance(seconds):
        clock[0] += round(seconds * 1000)

    with patch.object(asyncio, "sleep", side_effect=advance):
        asyncio.run(magnus.run_sequence(1))

    assert applied == [(0, 10), (500, 20)]
    assert clock[0] == 1500
    assert not magnus.active_sequence
    magnus.launcher.halt.assert_called_once()
    magnus.feeder.halt.assert_called_once()

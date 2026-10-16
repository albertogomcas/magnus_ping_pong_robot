import asyncio
import importlib.util
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import pytest


@pytest.fixture(scope="module")
def magnus_class():
    machine = ModuleType("machine")
    machine.Pin = MagicMock()
    machine.UART = MagicMock()

    parts = ModuleType("parts")
    for name in ("Feeder", "Launcher", "Aimer", "Shaker", "Detector", "Supply", "Remote", "ESPNowRemote"):
        setattr(parts, name, MagicMock())

    stservo_wrapper = ModuleType("stservo_wrapper")
    stservo_wrapper.STServo = MagicMock()
    stservo_package = ModuleType("stservo")
    stservo_package.__path__ = []
    port_handler = ModuleType("stservo.port_handler")
    port_handler.PortHandlerMicroPython = MagicMock()

    dev = ModuleType("dev")
    dev.DevFlags = type("DevFlags", (), {"simulation_mode": False})

    mocked_modules = {
        "machine": machine,
        "parts": parts,
        "stservo_wrapper": stservo_wrapper,
        "stservo": stservo_package,
        "stservo.port_handler": port_handler,
        "dev": dev,
        "microdot": MagicMock(),
    }
    path = os.path.join(os.path.dirname(__file__), "..", "..", "esp_app", "magnus.py")
    spec = importlib.util.spec_from_file_location("magnus_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, mocked_modules):
        spec.loader.exec_module(module)
    return module.Magnus, module.asyncio


def make_magnus(magnus_class):
    magnus = magnus_class.__new__(magnus_class)
    magnus.launcher = MagicMock()
    magnus.feeder = MagicMock()
    magnus.detector = MagicMock()
    magnus.sequence = []
    magnus.active_sequence = False
    magnus._randomize_sequence = False
    magnus._sequence_idx = 0
    magnus._sequence_generation = 0
    magnus._sequence_task = None
    magnus._watchdog_task = object()
    return magnus


def test_calibrate_yields_and_stops_launcher(magnus_class, monkeypatch):
    magnus_type, module_asyncio = magnus_class
    magnus = make_magnus(magnus_type)
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(module_asyncio, "sleep", fake_sleep)

    asyncio.run(magnus.calibrate())

    assert sleeps == [3, 1]
    magnus.launcher.set_speed.assert_has_calls([
        call("all", 100, force=True),
        call("all", 0),
    ])
    magnus.launcher.halt.assert_called_once()


def test_calibrate_stops_launcher_if_interrupted(magnus_class, monkeypatch):
    magnus_type, module_asyncio = magnus_class
    magnus = make_magnus(magnus_type)

    async def interrupt_calibration(_seconds):
        raise asyncio.CancelledError()

    monkeypatch.setattr(module_asyncio, "sleep", interrupt_calibration)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(magnus.calibrate())

    magnus.launcher.halt.assert_called_once()
    magnus.launcher.set_speed.assert_called_with("all", 0)


def test_start_sequence_rejects_empty_sequence(magnus_class):
    magnus_type, _ = magnus_class
    magnus = make_magnus(magnus_type)

    with pytest.raises(ValueError, match="empty sequence"):
        magnus.start_sequence()


def test_start_sequence_rejects_a_second_task(magnus_class):
    magnus_type, _ = magnus_class
    magnus = make_magnus(magnus_type)
    magnus.sequence = [{"speed": 50}]
    magnus._sequence_task = object()

    with pytest.raises(RuntimeError, match="already running or stopping"):
        magnus.start_sequence()


def test_stop_sequence_stops_launcher_and_feeder(magnus_class):
    magnus_type, _ = magnus_class
    magnus = make_magnus(magnus_type)
    task = MagicMock()
    magnus.active_sequence = True
    magnus._sequence_task = task

    magnus.stop_sequence()

    assert magnus.active_sequence is False
    assert magnus._sequence_task is None
    task.cancel.assert_called_once()
    magnus.launcher.halt.assert_called_once()
    magnus.feeder.halt.assert_called_once()


def test_old_sequence_cleanup_does_not_stop_new_sequence(magnus_class):
    magnus_type, _ = magnus_class
    magnus = make_magnus(magnus_type)
    magnus.active_sequence = True
    magnus._sequence_generation = 1
    magnus._sequence_task = object()

    asyncio.run(magnus.run_sequence(0))

    assert magnus.active_sequence is True
    assert magnus._sequence_task is not None
    magnus.launcher.halt.assert_not_called()


def test_wait_detector_returns_promptly_after_stop(magnus_class, monkeypatch):
    magnus_type, module_asyncio = magnus_class
    magnus = make_magnus(magnus_type)
    magnus.active_sequence = True

    async def stop_during_wait(_milliseconds):
        magnus.active_sequence = False

    monkeypatch.setattr(module_asyncio, "sleep_ms", stop_during_wait, raising=False)

    assert asyncio.run(magnus.wait_detector(magnus._sequence_generation)) is False
    magnus.detector.status.assert_not_called()


def test_run_sequence_cleans_up_after_stop(magnus_class, monkeypatch):
    magnus_type, module_asyncio = magnus_class
    magnus = make_magnus(magnus_type)
    magnus.sequence = [{"speed": 50}]
    magnus.active_sequence = True
    magnus.set_settings = MagicMock()
    magnus.flush_servo_uart = MagicMock()

    async def fake_sleep(_seconds):
        return None

    async def detector_stopped():
        return False

    monkeypatch.setattr(module_asyncio, "sleep", fake_sleep)
    magnus.wait_detector = lambda _generation: detector_stopped()

    asyncio.run(magnus.run_sequence(magnus._sequence_generation))

    assert magnus.active_sequence is False
    assert magnus._sequence_task is None
    magnus.launcher.halt.assert_called_once()

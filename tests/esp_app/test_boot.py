import importlib.util
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import pytest


@pytest.fixture(scope="module")
def boot_module():
    machine = ModuleType("machine")
    machine.UART = MagicMock()
    machine.Pin = MagicMock()

    network = ModuleType("network")
    network.STA_IF = 0
    network.WLAN = MagicMock()

    secrets = ModuleType("secrets")
    secrets.Wifi = type("Wifi", (), {"ssid": "test-ssid", "password": "test-password"})

    dev = ModuleType("dev")
    dev.DevFlags = type("DevFlags", (), {"simulation_mode": False, "run_app": True})

    gc = ModuleType("gc")
    gc.collect = MagicMock()
    gc.mem_free = MagicMock(return_value=1000)

    magnus = ModuleType("magnus")
    magnus._preallocated_uart = None

    mocked_modules = {
        "machine": machine,
        "network": network,
        "secrets": secrets,
        "dev": dev,
        "gc": gc,
        "magnus": magnus,
    }
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "esp_app", "boot.py"))
    spec = importlib.util.spec_from_file_location("boot_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, mocked_modules):
        spec.loader.exec_module(module)
    return module


def test_exists_file_exists(boot_module, monkeypatch):
    monkeypatch.setattr(boot_module.os, "stat", lambda _path: object())

    assert boot_module.exists("present.txt") is True


def test_exists_file_does_not_exist(boot_module, monkeypatch):
    def missing_file(_path):
        raise OSError

    monkeypatch.setattr(boot_module.os, "stat", missing_file)

    assert boot_module.exists("missing.txt") is False


def test_connect_configures_and_connects_wifi(boot_module, monkeypatch):
    nic = MagicMock()
    nic.isconnected.side_effect = [False, True]
    boot_module.network.WLAN.return_value = nic
    times = iter((0, 1, 2))
    monkeypatch.setattr(boot_module.time, "time", lambda: next(times))

    boot_module.connect()

    boot_module.network.WLAN.assert_called_once_with(boot_module.network.STA_IF)
    nic.active.assert_called_once_with(True)
    nic.connect.assert_called_once_with("test-ssid", "test-password")
    nic.ifconfig.assert_has_calls([
        call(("10.0.0.47", "255.255.255.0", "10.0.0.138", "8.8.8.8")),
        call(),
    ])


def test_connect_times_out(boot_module, monkeypatch):
    nic = MagicMock()
    nic.isconnected.return_value = False
    boot_module.network.WLAN.return_value = nic
    times = iter((0, 11))
    monkeypatch.setattr(boot_module.time, "time", lambda: next(times))

    with pytest.raises(RuntimeWarning, match="Could not connect"):
        boot_module.connect()

import importlib.util
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def webmain_module():
    machine = ModuleType("machine")
    machine.reset = MagicMock()

    network = ModuleType("network")
    network.STA_IF = 0
    nic = MagicMock()
    nic.isconnected.return_value = True
    nic.config.return_value = 6
    network.WLAN = MagicMock(return_value=nic)

    microdot = ModuleType("microdot")

    class FakeResponse:
        default_content_type = None

    class FakeMicrodot:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn

        def route(self, *_args, **_kwargs):
            return lambda fn: fn

        def shutdown(self):
            pass

    microdot.Response = FakeResponse
    microdot.Microdot = FakeMicrodot

    class FakeJRPCService:
        def __init__(self, api_version):
            self.api_version = api_version
            self.debug = False
            self.methods = {}

        def fn(self, name=None):
            def register(fn):
                self.methods[name or fn.__name__] = fn
                return fn
            return register

        def handle_rpc(self, request):
            return request

    ujrpc = ModuleType("ujrpc")
    ujrpc.JRPCService = FakeJRPCService

    dev = ModuleType("dev")
    dev.DevFlags = type("DevFlags", (), {"debug": False, "simulation_mode": False})

    gc = ModuleType("gc")
    gc.collect = MagicMock()
    gc.mem_free = MagicMock(return_value=1000)

    secrets = ModuleType("secrets")
    secrets.Wifi = type("Wifi", (), {"ssid": "test-ssid", "password": "test-password"})

    magnus_module = ModuleType("magnus")
    magnus_module.UsedPins = type("UsedPins", (), {"sanity_check": classmethod(lambda cls: None)})
    magnus_instance = MagicMock()
    magnus_module.Magnus = MagicMock(return_value=magnus_instance)

    mocked_modules = {
        "machine": machine,
        "network": network,
        "microdot": microdot,
        "ujrpc": ujrpc,
        "dev": dev,
        "gc": gc,
        "secrets": secrets,
        "magnus": magnus_module,
    }
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "esp_app", "webmain.py"))
    spec = importlib.util.spec_from_file_location("webmain_for_tests", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, mocked_modules):
        spec.loader.exec_module(module)
    return module, magnus_instance


def test_rpc_methods_are_registered(webmain_module):
    module, _ = webmain_module

    assert {"status", "set_aim", "set_launcher", "start_sequence", "stop_sequence"} <= set(module.jrpc.methods)


def test_set_aim_preserves_omitted_axis(webmain_module):
    module, magnus = webmain_module
    magnus.aimer.status.return_value = {"tilt": 8, "pan": -3}

    module.set_aim(None, tilt=12)

    magnus.aimer.aim.assert_called_once_with(vangle=12, hangle=-3)


def test_set_launcher_converts_spin_and_preserves_active_state(webmain_module):
    module, magnus = webmain_module
    magnus.launcher.status.return_value = {
        "speed": 40,
        "spin_angle": 0,
        "spin_strength": 0,
        "active": True,
    }

    module.set_launcher(None, speed=60, spin_angle=90, spin_strength=50)

    magnus.launcher.configure.assert_called_once()
    kwargs = magnus.launcher.configure.call_args.kwargs
    assert kwargs["speed"] == 60
    assert kwargs["topspin"] == pytest.approx(0)
    assert kwargs["sidespin"] == pytest.approx(0.5)
    magnus.launcher.activate.assert_called_once()


def test_start_sequence_forwards_settings(webmain_module):
    module, magnus = webmain_module
    settings = {"randomize_order": True, "feed_interval": 2}

    module.start_sequence(None, settings)

    magnus.start_sequence.assert_called_once_with(randomize_order=True, feed_interval=2)


def test_stop_sequence_stops_sequence(webmain_module):
    module, magnus = webmain_module

    module.stop_sequence(None)

    magnus.stop_sequence.assert_called_once_with()


def test_status_returns_current_robot_status(webmain_module):
    module, magnus = webmain_module
    magnus.status.return_value = {"launcher": {"active": True}}

    assert module.status(None) == {"launcher": {"active": True}}

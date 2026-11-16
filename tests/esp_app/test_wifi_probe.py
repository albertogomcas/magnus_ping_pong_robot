import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


path = Path(__file__).resolve().parents[2] / "esp_app" / "wifi_probe.py"
spec = importlib.util.spec_from_file_location("wifi_probe", path)
wifi_probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi_probe)


class FakeNic:
    def __init__(self, scan, successful=()):
        self.results = scan
        self.successful = successful
        self.attempts = []
        self.disconnections = 0

    def scan(self):
        if isinstance(self.results, Exception):
            raise self.results
        return self.results

    def connect(self, ssid, password):
        self.attempts.append((ssid, password))

    def isconnected(self):
        return bool(self.attempts) and self.attempts[-1][0] in self.successful

    def disconnect(self):
        self.disconnections += 1

    def status(self):
        return -1

    def config(self, key):
        assert key == "channel"
        return 6


@pytest.fixture
def credentials():
    return SimpleNamespace(ssid="primary", password="one",
                           ssid_alternate="alternate", password_alternate="two")


def scan_entry(ssid, rssi):
    return (ssid.encode(), b"", 6, rssi, 0, False)


def test_strongest_network_and_strongest_duplicate(credentials):
    nic = FakeNic([scan_entry("primary", -75), scan_entry("alternate", -55),
                   scan_entry("primary", -40)], successful=("primary",))
    assert wifi_probe.connect_strongest(nic, credentials) == "primary"
    assert nic.attempts == [("primary", "one")]


def test_alternate_network_selected_when_stronger(credentials):
    nic = FakeNic([scan_entry("primary", -75), scan_entry("alternate", -40)],
                  successful=("alternate",))
    assert wifi_probe.connect_strongest(nic, credentials) == "alternate"
    assert nic.attempts == [("alternate", "two")]


def test_failed_strongest_falls_back(credentials, monkeypatch):
    nic = FakeNic([scan_entry("primary", -80), scan_entry("alternate", -40)],
                  successful=("primary",))
    clock = iter([0, 0, 11, 12, 12])
    monkeypatch.setattr(wifi_probe.time, "time", lambda: next(clock))
    monkeypatch.setattr(wifi_probe.time, "sleep", lambda _: None)
    assert wifi_probe.connect_strongest(nic, credentials) == "primary"
    assert nic.attempts == [("alternate", "two"), ("primary", "one")]
    assert nic.disconnections == 1


def test_scan_failure_and_unseen_networks_use_configured_order(credentials):
    networks = wifi_probe.configured_networks(credentials)
    assert wifi_probe.ranked_networks(FakeNic(OSError("scan error")), networks) == networks
    assert wifi_probe.ranked_networks(FakeNic(RuntimeError("scan error")), networks) == networks
    assert wifi_probe.ranked_networks(FakeNic([]), networks) == networks


def test_single_network_and_incomplete_alternate():
    single = SimpleNamespace(ssid="primary", password="one")
    assert wifi_probe.configured_networks(single) == [("primary", "one")]
    single.ssid_alternate = "alternate"
    with pytest.raises(ValueError, match="password_alternate"):
        wifi_probe.configured_networks(single)


def test_all_connections_fail(credentials, monkeypatch):
    nic = FakeNic([])
    clock = iter([0, 11, 12, 23])
    monkeypatch.setattr(wifi_probe.time, "time", lambda: next(clock))
    with pytest.raises(RuntimeError, match="any configured"):
        wifi_probe.connect_strongest(nic, credentials)
    assert nic.disconnections == 2

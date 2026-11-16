import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


def load_sender():
    path = Path(__file__).resolve().parents[2] / "esp_app" / "remote_device" / "espnow_sender.py"
    spec = importlib.util.spec_from_file_location("test_espnow_sender", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"network": ModuleType("network"),
                                  "espnow": ModuleType("espnow"),
                                  "wifi_probe": SimpleNamespace(connect_strongest=None)}):
        spec.loader.exec_module(module)
    return module.ESPNowSender


def test_channel_search_and_response_reset():
    sender_class = load_sender()
    sender = sender_class.__new__(sender_class)
    sender.channel = 13
    sender.unanswered_requests = 0
    sender.receiver_mac = b"robot"
    channels = []
    sent = []
    sender.sta = SimpleNamespace(config=lambda **kw: channels.append(kw["channel"]))
    sender.send = lambda message: sent.append(message)
    sender.esp = SimpleNamespace(recv=lambda _: (b"robot", b'{"type":"status_response"}'))

    for _ in range(3):
        sender.probe_status()
    assert channels == []
    sender.probe_status()
    assert channels == [1]
    assert len(sent) == 4
    sender.receive()
    for _ in range(3):
        sender.probe_status()
    assert channels == [1]
    sender.probe_status()
    assert channels == [1, 2]


def test_unrelated_peer_does_not_stop_search():
    sender_class = load_sender()
    sender = sender_class.__new__(sender_class)
    sender.receiver_mac = b"robot"
    sender.unanswered_requests = 2
    sender.esp = SimpleNamespace(recv=lambda _: (b"other", b'{"type":"status_response"}'))
    assert sender.receive() is None
    assert sender.unanswered_requests == 2


def test_search_skips_unsupported_channel():
    sender_class = load_sender()
    sender = sender_class.__new__(sender_class)
    sender.channel = 11
    sender.unanswered_requests = 3
    channels = []

    def set_channel(**kwargs):
        channel = kwargs["channel"]
        if channel == 12:
            raise OSError("unsupported")
        channels.append(channel)

    sender.sta = SimpleNamespace(config=set_channel)
    sender.send = lambda message: None
    sender.probe_status()
    sender.probe_status()
    assert channels == [13]


def test_send_reports_missing_acknowledgement():
    sender_class = load_sender()
    sender = sender_class.__new__(sender_class)
    sender.receiver_mac = b"robot"
    sender.esp = SimpleNamespace(send=lambda *_: False)
    assert sender.send({"type": "key_press"}) is False

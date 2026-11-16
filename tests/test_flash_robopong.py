import hashlib
import importlib.util
from pathlib import Path

import pytest


path = Path(__file__).resolve().parents[1] / ".github" / "skills" / "flash-robopong" / "flash.py"
spec = importlib.util.spec_from_file_location("flash_robopong", path)
flash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flash)


def test_robot_upload_verifies_before_reset(tmp_path, monkeypatch):
    source = tmp_path / "parts.py"
    source.write_bytes(b"robot code")
    monkeypatch.setattr(flash, "ROBOT_FILES", {"parts.py": source})
    calls = []

    def command(port, *args):
        calls.append((port, args))
        if args[0] == "exec":
            return "DEVICE_ID: Generic ESP32 module with ESP32\n"
        if args[:2] == ("fs", "sha256sum"):
            return "sha256sum :parts.py\n" + hashlib.sha256(source.read_bytes()).hexdigest()
        return ""

    monkeypatch.setattr(flash, "command", command)
    monkeypatch.setattr(flash, "observe_startup", lambda port, device: True)
    assert flash.flash("robot", "COM4", ["parts.py"])
    assert [args[0] for _, args in calls] == ["exec", "fs", "fs", "reset"]


def test_hash_mismatch_does_not_reset(tmp_path, monkeypatch):
    source = tmp_path / "main.py"
    source.write_bytes(b"remote code")
    monkeypatch.setattr(flash, "REMOTE_FILES", {"main.py": source})
    calls = []

    def command(port, *args):
        calls.append(args)
        if args[0] == "exec":
            return "DEVICE_ID: ESP32C6 module with ESP32C6\n"
        if args[:2] == ("fs", "sha256sum"):
            return "sha256sum :main.py\n" + "0" * 64
        return ""

    monkeypatch.setattr(flash, "command", command)
    with pytest.raises(RuntimeError, match="Hash verification failed"):
        flash.flash("remote", "COM3", ["main.py"])
    assert not any(args[0] == "reset" for args in calls)


def test_wrong_board_and_unapproved_files_are_rejected(monkeypatch):
    calls = []
    monkeypatch.setattr(
        flash, "command",
        lambda port, *args: calls.append(args) or "DEVICE_ID: ESP32C6 module with ESP32C6\n",
    )
    with pytest.raises(RuntimeError, match="Board type"):
        flash.flash("robot", "COM3", ["parts.py"])
    with pytest.raises(ValueError, match="Unsupported"):
        flash.flash("robot", "COM4", ["secrets.py"])
    assert [args[0] for args in calls] == ["exec"]

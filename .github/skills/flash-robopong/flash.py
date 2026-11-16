"""Transfer selected MicroPython files without exposing device configuration."""

import argparse
import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ROBOT_FILES = {
    name: ROOT / "esp_app" / name
    for name in (
        "magnus.py", "parts.py", "stservo_wrapper.py", "webmain.py",
        "drill_store.py", "wifi_probe.py", "ujrpc.py", "dev.py", "main.py",
    )
}
REMOTE_FILES = {
    name: ROOT / "esp_app" / "remote_device" / name
    for name in ("main.py", "keypad.py", "oled_display.py", "espnow_sender.py", "ssd1306.py")
}
REMOTE_FILES["wifi_probe.py"] = ROOT / "esp_app" / "wifi_probe.py"


def command(port, *args):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mpremote", "connect", port, *args],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Device command timed out; check connection and port.") from exc
    if result.returncode:
        detail = result.stderr.lower()
        if "no module named mpremote" in detail:
            raise RuntimeError("mpremote is not installed for this Python interpreter.")
        if "failed to access" in detail or "access is denied" in detail:
            raise RuntimeError("Cannot access port; check connection and whether it is in use.")
        raise RuntimeError("Device command failed (exit {}).".format(result.returncode))
    return result.stdout


def parse_hashes(output):
    pairs = re.findall(r"sha256sum\s+:([^\s]+)\s+([0-9a-fA-F]{64})", output)
    return {name: digest.lower() for name, digest in pairs}


def observe_startup(port, device, seconds=25):
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial is not installed for this Python interpreter.") from exc
    try:
        connection = serial.Serial(port=None, baudrate=115200, timeout=1)
        connection.dtr = False
        connection.rts = False
        connection.port = port
        connection.open()
        with connection:
            end = time.monotonic() + seconds
            markers = (
                ("[ESPNowRemote] Starting receiver loop", "[ESPNowRemote] Received message",
                 "Sent status successfully")
                if device == "robot"
                else ("[Remote] Starting remote controller", "Parsed data type: status_response")
            )
            while time.monotonic() < end:
                line = connection.readline().decode("utf-8", "replace")
                if any(marker in line for marker in markers):
                    return True
    except serial.SerialException:
        return False
    return False


def flash(device, port, names):
    available = ROBOT_FILES if device == "robot" else REMOTE_FILES
    invalid = [name for name in names if name not in available]
    if invalid:
        raise ValueError("Unsupported file(s): " + ", ".join(invalid))
    if len(set(names)) != len(names):
        raise ValueError("Do not specify the same file more than once.")
    for name in names:
        if not available[name].is_file():
            raise ValueError("Local application file is missing: " + name)

    identity = command(port, "exec", "import os; print('DEVICE_ID:', os.uname().machine)")
    match = re.search(r"DEVICE_ID:\s*([^\r\n]+)", identity)
    if not match:
        raise RuntimeError("Could not verify device identity; nothing was uploaded.")
    machine = match.group(1).strip().lower()
    valid = ("esp32c6" in machine if device == "remote"
             else "esp32" in machine and "esp32c6" not in machine)
    if not valid:
        raise RuntimeError("Board type does not match the selected device; nothing was uploaded.")

    try:
        command(port, "fs", "cp", *(str(available[name]) for name in names), ":")
        remote = parse_hashes(command(port, "fs", "sha256sum", *(":" + name for name in names)))
        mismatched = [
            name for name in names
            if hashlib.sha256(available[name].read_bytes()).hexdigest() != remote.get(name)
        ]
        if mismatched:
            raise RuntimeError("Hash verification failed: " + ", ".join(mismatched))
    except RuntimeError as exc:
        raise RuntimeError(str(exc) + " The update may be partial; do not reset until resolved.") from exc

    print("{}: verified {}".format(device, ", ".join(names)), flush=True)
    command(port, "reset")
    if observe_startup(port, device):
        print("{}: restarted; application activity observed".format(device))
    else:
        print("{}: reset sent; application startup not observed".format(device))
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", choices=("robot", "remote"))
    parser.add_argument("--port", required=True)
    parser.add_argument("--files", required=True, nargs="+")
    args = parser.parse_args()
    try:
        return 0 if flash(args.device, args.port, args.files) else 2
    except (RuntimeError, ValueError, OSError) as exc:
        print("Flash failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

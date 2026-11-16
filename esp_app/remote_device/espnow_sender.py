"""
ESP-NOW Sender for Remote Control
"""
import espnow
import network
import json
import time
from wifi_probe import connect_strongest


class ESPNowSender:
    def __init__(self, receiver_mac, wifi=None, channel=None):
        """
        Initialize ESP-NOW sender
        receiver_mac: MAC address of receiver as bytes (e.g., b'\xaa\xbb\xcc\xdd\xee\xff')
        wifi: Wifi credentials class (optional)
        channel: WiFi channel (1-13) - if None, will auto-detect from WiFi connection
        """
        # Initialize WiFi in station mode (required for ESP-NOW)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)

        print(f"[ESPNow] My MAC: {self._mac_to_str(self.sta.config('mac'))}")

        # Auto-detect channel from WiFi if credentials provided
        if channel is None and wifi is not None:
            try:
                connect_strongest(self.sta, wifi)
                channel = self.sta.config('channel')
                self.sta.disconnect()
                time.sleep(0.5)
                print(f"[ESPNow] Disconnected from WiFi, continuing with ESP-NOW on channel {channel}")
            except RuntimeError as exc:
                print(f"[ESPNow] WARNING: {exc}; searching for robot from channel 1")
                channel = 1
        elif channel is None:
            print(f"[ESPNow] WARNING: No WiFi credentials or channel provided, using default channel 1")
            channel = 1

        # Set WiFi channel (critical for ESP-NOW communication)
        self.sta.config(channel=channel)
        self.channel = channel
        self.unanswered_requests = 0
        print(f"[ESPNow] WiFi channel set to {channel}")

        # Initialize ESP-NOW
        self.esp = espnow.ESPNow()
        self.esp.active(True)

        # Add peer
        self.receiver_mac = receiver_mac
        self.esp.add_peer(receiver_mac)

        print(f"[ESPNow] Initialized, receiver MAC: {self._mac_to_str(receiver_mac)}")

    def probe_status(self):
        """Search channels until the robot answers a status request."""
        if self.unanswered_requests >= 3:
            self.channel = self.channel % 13 + 1
            try:
                self.sta.config(channel=self.channel)
            except OSError as exc:
                print(f"[ESPNow] Cannot use channel {self.channel}: {exc}")
                return
            self.unanswered_requests = 0
            print(f"[ESPNow] Searching for robot on channel {self.channel}")
        self.send({'type': 'status_request', 'timestamp': time.time()})
        self.unanswered_requests += 1

    def _mac_to_str(self, mac):
        """Convert MAC address bytes to string"""
        return ':'.join(['%02x' % b for b in mac])

    def send(self, message):
        """
        Send message via ESP-NOW
        message: dict to be JSON encoded
        """
        try:
            json_msg = json.dumps(message)
            self.esp.send(self.receiver_mac, json_msg)
            print(f"[ESPNow] Sent: {json_msg[:50]}...")  # Show first 50 chars
            return True
        except Exception as e:
            print(f"[ESPNow] Send error: {e}")
            return False

    def receive(self):
        """
        Check for received messages
        Returns: dict or None
        """
        try:
            host, msg = self.esp.recv(0)  # Non-blocking
            if msg and host == self.receiver_mac:
                print(f"[ESPNow] Received from {self._mac_to_str(host)}: {msg[:100]}...")
                data = json.loads(msg)
                if data.get('type') == 'status_response':
                    self.unanswered_requests = 0
                print(f"[ESPNow] Parsed data type: {data.get('type')}")
                return data
        except Exception as e:
            # Only print actual errors, not "no message" cases
            if str(e) != "None":
                print(f"[ESPNow] Receive error: {e}")
        return None

    def get_my_mac(self):
        """Get this device's MAC address"""
        return self.sta.config('mac')

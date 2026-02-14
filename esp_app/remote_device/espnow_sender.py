"""
ESP-NOW Sender for Remote Control
"""
import espnow
import network
import json


class ESPNowSender:
    def __init__(self, receiver_mac, channel=1):
        """
        Initialize ESP-NOW sender
        receiver_mac: MAC address of receiver as bytes (e.g., b'\xaa\xbb\xcc\xdd\xee\xff')
        channel: WiFi channel (1-13, default 1) - must match receiver
        """
        # Initialize WiFi in station mode (required for ESP-NOW)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)

        # Set WiFi channel (critical for ESP-NOW communication)
        self.sta.config(channel=channel)
        print(f"[ESPNow] WiFi channel set to {channel}")

        # Initialize ESP-NOW
        self.esp = espnow.ESPNow()
        self.esp.active(True)

        # Add peer
        self.receiver_mac = receiver_mac
        self.esp.add_peer(receiver_mac)

        print(f"[ESPNow] Initialized, receiver MAC: {self._mac_to_str(receiver_mac)}")
        print(f"[ESPNow] My MAC: {self._mac_to_str(self.sta.config('mac'))}")

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
            if msg:
                return json.loads(msg)
        except Exception as e:
            pass
        return None

    def get_my_mac(self):
        """Get this device's MAC address"""
        return self.sta.config('mac')

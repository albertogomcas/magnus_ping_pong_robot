"""
ESP-NOW Sender for Remote Control
"""
import espnow
import network
import json
import time


class ESPNowSender:
    def __init__(self, receiver_mac, wifi_ssid=None, wifi_password=None, channel=None):
        """
        Initialize ESP-NOW sender
        receiver_mac: MAC address of receiver as bytes (e.g., b'\xaa\xbb\xcc\xdd\xee\xff')
        wifi_ssid: WiFi SSID to connect to get channel (optional)
        wifi_password: WiFi password (optional)
        channel: WiFi channel (1-13) - if None, will auto-detect from WiFi connection
        """
        # Initialize WiFi in station mode (required for ESP-NOW)
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)

        print(f"[ESPNow] My MAC: {self._mac_to_str(self.sta.config('mac'))}")

        # Auto-detect channel from WiFi if credentials provided
        if channel is None and wifi_ssid:
            print(f"[ESPNow] Connecting to WiFi '{wifi_ssid}' to detect channel...")
            self.sta.connect(wifi_ssid, wifi_password)

            # Wait for connection (max 10 seconds)
            timeout = 10
            start = time.time()
            while not self.sta.isconnected() and (time.time() - start) < timeout:
                time.sleep(0.5)

            if self.sta.isconnected():
                # Get the channel from the connected WiFi
                channel = self.sta.config('channel')
                print(f"[ESPNow] WiFi connected on channel {channel}")
                print(f"[ESPNow] IP: {self.sta.ifconfig()[0]}")

                # Disconnect from WiFi (we only needed to get the channel)
                self.sta.disconnect()
                time.sleep(0.5)
                print(f"[ESPNow] Disconnected from WiFi, continuing with ESP-NOW on channel {channel}")
            else:
                print(f"[ESPNow] WARNING: Could not connect to WiFi, using default channel 1")
                channel = 1
        elif channel is None:
            print(f"[ESPNow] WARNING: No WiFi credentials or channel provided, using default channel 1")
            channel = 1

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
                print(f"[ESPNow] Received from {self._mac_to_str(host)}: {msg[:100]}...")
                data = json.loads(msg)
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

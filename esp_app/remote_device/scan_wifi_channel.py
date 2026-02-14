"""
Scan WiFi networks to find the channel of the receiver's WiFi network
Run this on the remote device to determine which channel to use
"""
import network

def scan_wifi():
    """Scan for WiFi networks and display channels"""
    print("Scanning WiFi networks...")
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    networks = sta.scan()

    print("\nAvailable WiFi Networks:")
    print("-" * 60)
    print(f"{'SSID':<32} {'Channel':<8} {'RSSI':<8}")
    print("-" * 60)

    for net in networks:
        ssid = net[0].decode('utf-8')
        channel = net[2]
        rssi = net[3]
        print(f"{ssid:<32} {channel:<8} {rssi:<8}")

    print("-" * 60)
    print("\nTo use ESP-NOW with the receiver:")
    print("1. Find the SSID that the receiver is connected to")
    print("2. Note its channel number")
    print("3. Update remote_device/main.py:")
    print("   self.sender = ESPNowSender(RECEIVER_MAC, channel=X)")
    print("\nExample: If receiver is on channel 6:")
    print("   self.sender = ESPNowSender(RECEIVER_MAC, channel=6)")

if __name__ == "__main__":
    scan_wifi()

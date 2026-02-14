"""
Display the WiFi channel that the receiver is using
Run this on the receiver to see what channel the remote should use
"""
import network

def show_wifi_info():
    """Display WiFi connection information"""
    sta = network.WLAN(network.STA_IF)

    if not sta.active():
        print("WiFi is not active!")
        return

    if not sta.isconnected():
        print("WiFi is not connected!")
        return

    channel = sta.config('channel')
    mac = sta.config('mac')
    mac_str = ':'.join(['%02x' % b for b in mac])
    ifconfig = sta.ifconfig()

    print("=" * 60)
    print("RECEIVER WiFi INFORMATION")
    print("=" * 60)
    print(f"MAC Address:  {mac_str}")
    print(f"IP Address:   {ifconfig[0]}")
    print(f"WiFi Channel: {channel}")
    print("=" * 60)
    print("\nTo configure the remote:")
    print(f"1. Set RECEIVER_MAC = b'\\x{'\\x'.join([f'{b:02x}' for b in mac])}'")
    print(f"2. Set channel={channel} in ESPNowSender initialization:")
    print(f"   self.sender = ESPNowSender(RECEIVER_MAC, channel={channel})")
    print("=" * 60)

if __name__ == "__main__":
    show_wifi_info()

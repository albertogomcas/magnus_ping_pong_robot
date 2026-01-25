"""
Helper script to get the MAC address of the ESP32
Run this on each ESP32 device to get its MAC address for configuration
"""
import network

def get_mac_addresses():
    """Get MAC addresses for both STA and AP interfaces"""
    sta = network.WLAN(network.STA_IF)
    ap = network.WLAN(network.AP_IF)

    sta.active(True)
    ap.active(True)

    sta_mac = sta.config('mac')
    ap_mac = ap.config('mac')

    print("=" * 50)
    print("ESP32 MAC Addresses")
    print("=" * 50)
    print(f"STA (Station) MAC: {mac_to_str(sta_mac)}")
    print(f"  As bytes: {mac_to_bytes_str(sta_mac)}")
    print()
    print(f"AP (Access Point) MAC: {mac_to_str(ap_mac)}")
    print(f"  As bytes: {mac_to_bytes_str(ap_mac)}")
    print("=" * 50)
    print()
    print("Copy the 'As bytes' format into your code:")
    print("  RECEIVER_MAC = " + mac_to_bytes_str(sta_mac))

def mac_to_str(mac):
    """Convert MAC bytes to readable string"""
    return ':'.join(['%02x' % b for b in mac])

def mac_to_bytes_str(mac):
    """Convert MAC to Python bytes literal"""
    return "b'" + ''.join(['\\x%02x' % b for b in mac]) + "'"

if __name__ == '__main__':
    get_mac_addresses()

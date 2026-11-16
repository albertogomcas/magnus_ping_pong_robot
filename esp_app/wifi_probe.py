"""Choose and connect to configured Wi-Fi networks on MicroPython."""
import time


def configured_networks(wifi):
    networks = []
    for ssid_name, password_name in (
        ("ssid", "password"), ("ssid_alternate", "password_alternate")
    ):
        ssid = getattr(wifi, ssid_name, None)
        password = getattr(wifi, password_name, None)
        if ssid:
            if password is None:
                raise ValueError("Missing Wi-Fi password: " + password_name)
            networks.append((ssid, password))
        elif password:
            raise ValueError("Missing Wi-Fi SSID: " + ssid_name)
    if not networks:
        raise ValueError("No Wi-Fi networks configured")
    return networks


def ranked_networks(nic, networks):
    try:
        scan = nic.scan()
    except (OSError, RuntimeError) as exc:
        print("[WiFi] Scan failed; trying configured order:", exc)
        return networks

    strengths = {}
    for entry in scan:
        ssid = entry[0]
        if isinstance(ssid, bytes):
            try:
                ssid = ssid.decode("utf-8")
            except UnicodeError:
                continue
        if ssid not in strengths or entry[3] > strengths[ssid]:
            strengths[ssid] = entry[3]
    # Also try hidden or temporarily unseen networks, after visible ones.
    return sorted(networks, key=lambda item: strengths.get(item[0], -1000), reverse=True)


def connect_strongest(nic, wifi, timeout=10):
    if nic.isconnected():
        nic.disconnect()
    networks = ranked_networks(nic, configured_networks(wifi))
    for ssid, password in networks:
        print("[WiFi] Connecting to", ssid)
        try:
            nic.connect(ssid, password)
            start = time.time()
            while time.time() - start < timeout:
                if nic.isconnected():
                    print("[WiFi] Connected to", ssid, "on channel", nic.config("channel"))
                    return ssid
                time.sleep(0.1)
            print("[WiFi] Connection timed out:", ssid, "status:", nic.status())
        except (OSError, RuntimeError) as exc:
            print("[WiFi] Connection failed:", ssid, exc)
        nic.disconnect()
    raise RuntimeError("Could not connect to any configured Wi-Fi network")

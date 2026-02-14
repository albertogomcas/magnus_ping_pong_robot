import time
import math
from machine import Pin, PWM, ADC, UART
import asyncio
from dev import DevFlags
import espnow
import network
import json


class Aimer:
    def __init__(self, vservo, hservo):
        self.vservo = vservo
        self.hservo = hservo

        self.vgain = -4
        self.hgain = -4
        self.vspeed = 50
        self.hspeed = 50

        self.vlim_min = -25
        self.vlim_max = 35

        self.hlim_min = -15
        self.hlim_max = 15

        self._shadow = (0, 0)


    def aim(self, vangle, hangle):
        vangle = min(max(self.vlim_min, vangle), self.vlim_max)
        hangle = min(max(self.hlim_min, hangle), self.hlim_max)

        print(f"[Aimer] aiming to {vangle}V {hangle}H")
        self._shadow = (180 + vangle*self.vgain, 180 + hangle*self.hgain)

        if not DevFlags.simulation_mode:
            self.vservo.move(180 + vangle*self.vgain, self.vspeed)
            self.hservo.move(180 + hangle*self.hgain, self.hspeed)


    def status(self):
        try:
            if not DevFlags.simulation_mode:
                vangle_raw = self.vservo.status()["angle"]
                hangle_raw = self.hservo.status()["angle"]
            else:
                vangle_raw, hangle_raw = self._shadow
        except:
            return dict(
                tilt=0,
                pan=0,
            )

        return dict(
            tilt=(vangle_raw - 180)/self.vgain,
            pan=(hangle_raw - 180)/self.hgain,
        )

    def calibrate(self):
        if not DevFlags.simulation_mode:
            self.vservo.calibrate_middle()
            self.hservo.calibrate_middle()
        return True

    def up(self):
        """Move up"""
        print("[Aimer] Up")
        st = self.status()
        self.aim(vangle=st["tilt"] + 1, hangle=st["pan"])

    def down(self):
        """Move down"""
        print("[Aimer] Down")
        st = self.status()
        self.aim(vangle=st["tilt"] - 1, hangle=st["pan"])

    def middle(self):
        """Move to middle position"""
        print("[Aimer] Middle")
        self.aim(vangle=0, hangle=0)

    def left(self):
        """Move left"""
        print("[Aimer] Left")
        st = self.status()
        self.aim(vangle=st["tilt"], hangle=st["pan"] - 1)

    def right(self):
        """Move right"""
        print("[Aimer] Right")
        st = self.status()
        self.aim(vangle=st["tilt"], hangle=st["pan"] + 1)



class Feeder:
    """Uses a st servo in wheel mode to feed balls into the launcher"""
    def __init__(self, st_servo, shaker):
        self.st_servo = st_servo
        self.shaker = shaker
        self.active = False
        self.interval = 4
        self.deg_ball = 60 # new ball every 60deg
        self.wait = 0.25

    def set_ball_interval(self, seconds):
        self.interval = max(0.5, seconds)
        print(f"[Feeder] ball interval set to {self.interval}s")

    async def feed_one(self):
        print("not implemented")

    async def run(self):
        while True:
            await asyncio.sleep(self.wait)
            if self.active:
                speed = self.deg_ball / self.interval
                if not DevFlags.simulation_mode:
                    self.st_servo.move(0, speed)
            else:
                try:
                    if not DevFlags.simulation_mode:
                        self.st_servo.move(0, 0)
                except:
                    pass

    def activate(self):
        print("[Feeder] Activate")
        self.active = True
        if self.shaker:
            self.shaker.active = True

    def halt(self):
        print("[Feeder] Halt")
        self.active = False
        if self.shaker:
            self.shaker.active = False

    def status(self):
        return dict(active=self.active, interval=self.interval)


class Shaker:
    """Uses a stservo to stir balls"""
    def __init__(self, st_servo):
        self.servo = st_servo
        self.active = False
        self.swing_angle = 130
        self.speed = 50
        self.acceleration = 2


    async def run(self):
        while True:
            await asyncio.sleep(0.1)
            if self.active:
                if self.active:
                    print("[Shaker] moving back")
                    if not DevFlags.simulation_mode:
                        self.servo.move(180 + self.swing_angle, self.speed, self.acceleration)
                    await asyncio.sleep(2.5*self.swing_angle/self.speed)
                if self.active:
                    print("[Shaker] moving forward")
                    if not DevFlags.simulation_mode:
                        self.servo.move(180 - self.swing_angle, self.speed, self.acceleration)
                    await asyncio.sleep(2.5*self.swing_angle/self.speed)
            else:
                try:
                    #print("[Shaker] stopping")
                    if not DevFlags.simulation_mode:
                        self.servo.move(180, self.speed, self.acceleration)
                except:
                    pass


class ESC:
    def __init__(self, pin, name, freq=50):
        self.pin = Pin(pin, Pin.OUT)
        self.name = name
        self.pwm = PWM(self.pin, freq=freq)
        self.min_pulse = 1000000  # ns
        self.max_pulse = 2000000  # ns
        self.speed = 0
        self._current_pulse = 0
        self.limit = 100
        self.set_speed(0)

    def calibrate_1(self):
        """Must be called before the ESC is powered up"""
        self.pwm.duty_ns(self.max_pulse)

    def calibrate_2(self):
        """Must be called after the ESC has powered up and entered programming mode"""
        self.pwm.duty_ns(self.min_pulse)

    def set_speed(self, speed_pc, force=False):
        if speed_pc > self.limit:
            print(f"[ESC] Capping speed to limit {self.limit}")
            speed_pc = self.limit
        if speed_pc <= 0:
            speed_pc = 0

        pulse = int(speed_pc / 100 * (self.max_pulse - self.min_pulse) + self.min_pulse)
        self.speed = speed_pc
        self._current_pulse = pulse

        if force:
            self.pwm.duty_ns(pulse)
            self.spin_up()

    def spin_up(self):
        self.pwm.duty_ns(self._current_pulse)

    def spin_down(self):
        """Stop the motor"""
        pulse = int(0 / 100 * (self.max_pulse - self.min_pulse) + self.min_pulse)
        self.pwm.duty_ns(pulse)

    def status(self):
        return f"{self.name}{self.speed:2.0f}"

class Detector:
    def __init__(self, pd_pin):
        self._pd_pin = pd_pin
        # Add pull-down resistor to prevent floating state
        self._pd = Pin(pd_pin, Pin.IN, Pin.PULL_DOWN)
        self._last_pulse = 0
        # 150ms debounce (since ball passage < 100ms, this filters noise)
        self._debounce = 0.15
        self._pd.irq(trigger=Pin.IRQ_RISING, handler=self.handle_detection)

    def handle_detection(self, pin):
        current_time = time.time()
        # Only register detection if enough time has passed since last one
        if current_time - self._last_pulse > self._debounce:
            print("[Detector] detected ball")
            self._last_pulse = current_time
        # else: ignore spurious trigger

    def status(self):
        if DevFlags.simulation_mode:
            # In simulation mode, we simulate a detection every 2.15 seconds
            if time.time() - self._last_pulse > 2.15:
                self._last_pulse = time.time()
                print("[Detector] simulated ball detection")

        return dict(elapsed=time.time() - self._last_pulse)


class Launcher:
    """Shoots balls using 3 brushless motors"""

    def __init__(self, top, left, right, feeder=None):
        self._esc = {
            "top": ESC(top, name="T"),
            "left": ESC(left, "L"),
            "right": ESC(right, "R"),
        }
        self.feeder = feeder

        self._cos30 = 0.866
        self._sin30 = 0.5

        self.raw_minimum = 5
        self.raw_maximum = 9
        self.raw_spin = 3 * 2 * self._cos30 * self.raw_minimum / 5 # should ensure does not go negative ever
        self.active = False
        self.speed = 0
        self.topspin = 0
        self.sidespin = 0
        self.left_speed = 0
        self.right_speed = 0
        self.top_speed = 0

    def set_speed(self, motor, percentage, force=False):
        assert 0 <= percentage <= 100

        assert motor in ["all", "top", "left", "right"]

        if motor == "all":
            for motor_name, motor_esc in self._esc.items():
                motor_esc.set_speed(percentage, force)

        else:
            self._esc[motor].set_speed(percentage, force)

    def speed_up(self):
        st = self.status()
        self.configure(speed=st["speed"]+2,
                       topspin=st["topspin"],
                       sidespin=st["sidespin"])
        self.activate()

    def speed_down(self):
        st = self.status()

        self.configure(speed=st["speed"]-2,
                       topspin=st["topspin"],
                       sidespin=st["sidespin"])
        self.activate()



    def increase_spin(self):
        st = self.status()
        self.configure(
            speed=st["speed"],
            topspin=st["topspin"]*1.1,
            sidespin=st["sidespin"]*1.1,
            activate=True,
        )

    def decrease_spin(self):
        st = self.status()
        self.configure(
            speed=st["speed"],
            topspin=st["topspin"]/1.1,
            sidespin=st["sidespin"]/1.1,
            activate=True,
        )

    def no_spin(self):
        """Set no spin"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0, sidespin=0, activate=True)

    def spin_T(self):
        """Set topspin only"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0.5, sidespin=0, activate=True)

    def spin_B(self):
        """Set backspin only"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=-0.5, sidespin=0, activate=True)

    def spin_L(self):
        """Set left sidespin only"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0, sidespin=-0.5, activate=True)

    def spin_R(self):
        """Set right sidespin only"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0, sidespin=0.5, activate=True)

    def spin_TL(self):
        """Set topspin and left sidespin"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0.5, sidespin=-0.5, activate=True)

    def spin_TR(self):
        """Set topspin and right sidespin"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=0.5, sidespin=0.5, activate=True)

    def spin_BL(self):
        """Set backspin and left sidespin"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=-0.5, sidespin=-0.5, activate=True)

    def spin_BR(self):
        """Set backspin and right sidespin"""
        st = self.status()
        self.configure(speed=st["speed"], topspin=-0.5, sidespin=0.5, activate=True)

    def spin_random(self):
        """Set random spin"""
        import random
        st = self.status()
        topspin = random.uniform(-1, 1)
        sidespin = random.uniform(-1, 1)
        self.configure(speed=st["speed"], topspin=topspin, sidespin=sidespin, activate=True)

    def activate(self):
        """Accelerate towards launching speed"""
        if self.speed > 0:
            for motor in self._esc.values():
                motor.spin_up()
            self.active = True
        else:
            print("[Launcher] Cannot activate, speed is 0")
            self.active = False

    def halt(self):
        """Turn off"""
        for motor in self._esc.values():
            motor.spin_down()
        self.active = False
        if self.feeder:
            self.feeder.halt()

    def configure(self, speed, topspin, sidespin, activate=False):
        speed = max(0, min(speed, 100))
        topspin = max(-1, min(topspin, 1))
        sidespin = max(-1, min(sidespin, 1))

        # base speed is the given setting
        if speed == 0:
            base_speed = 0
        else:
            base_speed = (self.raw_maximum - self.raw_minimum) * speed / 100 + self.raw_minimum

        top = topspin * self.raw_spin
        side = sidespin * self.raw_spin

        left_speed = (3 * base_speed - top - 3/2 * side / self._cos30) / 3
        right_speed = left_speed + side / self._cos30
        top_speed = top + self._sin30 * (left_speed + right_speed)

        if left_speed < self.raw_minimum:
            print("[Launcher] Warning: settings make left speed stall")
        if right_speed < self.raw_minimum:
            print("[Launcher] Warning: settings make right speed stall")
        if top_speed < self.raw_minimum:
            print("[Launcher] Warning: settings make top speed stall")

        left_speed = max(left_speed, 0)
        right_speed = max(right_speed, 0)
        top_speed = max(top_speed, 0)

        print(f"[Launcher] Requested speed {base_speed}, (T+L+R)/3 = {(top_speed + right_speed + left_speed) / 3}")

        print(f"[Launcher] Configuring for speed {speed}, top {topspin}, side {sidespin}")
        print(f"[Launcher] Top {top_speed:.1f}, Left {left_speed:.1f}, Right {right_speed:.1f}")

        if speed == 0:
            self.feeder.halt()

        self.speed = speed
        self.topspin = topspin
        self.sidespin = sidespin
        self.top_speed = top_speed
        self.right_speed = right_speed
        self.left_speed = left_speed

        self._esc["top"].set_speed(top_speed)
        self._esc["left"].set_speed(left_speed)
        self._esc["right"].set_speed(right_speed)

        if activate:
            self.activate()

    def status(self):
        # topspin = math.cos(math.radians(spin_angle)) * spin_strength / 100
        # sidespin = math.sin(math.radians(spin_angle)) * spin_strength / 100
        return dict(
            active=self.active,
            speed=self.speed,
            top_speed=self.top_speed,
            right_speed=self.right_speed,
            left_speed=self.left_speed,
            topspin=self.topspin,
            sidespin=self.sidespin,
            spin_angle= math.degrees(math.atan2(self.sidespin, self.topspin)) if self.topspin != 0 else 0,
            spin_strength=math.sqrt(self.topspin**2 + self.sidespin**2) * 100,
        )


class Supply():
    def __init__(self, alive_pin):
        self.esc_alive_pin = ADC(Pin(alive_pin))

    def esc_alive(self):
        if DevFlags.simulation_mode:
            return True
        return self.esc_alive_pin.read() > 3500

    def status(self):
        return dict(
            esc_alive=self.esc_alive(),
        )

class Remote:
    def __init__(self, rx_pin):
        self.rx_pin = Pin(rx_pin, Pin.IN)
        self.uart = UART(2, rx=self.rx_pin, baudrate=9600, bits=8, parity=None, stop=1)

        self.commands = {
            "CH-": "BA45FF00",
            "CH": "B946FF00",
            "CH+": "B847FF00",
            "PREV": "BB44FF00",
            "NEXT": "BF40FF00",
            "PLAY": "BC43FF00",
            "VOL-": "F807FF00",
            "VOL+": "EA15FF00",
            "EQ": "F609FF00",
            "0": "E916FF00",
            "100+": "E619FF00",
            "200+": "F20DFF00",
            "1": "F30CFF00",
            "2": "E718FF00",
            "3": "A15EFF00",
            "4": "F708FF00",
            "5": "E31CFF00",
            "6": "A55AFF00",
            "7": "BD42FF00",
            "8": "AD52FF00",
            "9": "B54AFF00",
        }

        self.actions = {}

    def bind(self, ckey, action):
        """Bind a command key to an action"""
        if ckey not in self.commands:
            raise ValueError(f"Command {ckey} not found")
        self.actions[self.commands[ckey]] = action

    def handle_command(self, command):
        """Handle a command received from the remote"""
        if command in self.actions:
            print(f"[Remote] Executing action for command {command}")
            self.actions[command]()
        else:
            print(f"[Remote] No action bound for command {command}")

    async def run(self):
        """Run the remote handler"""
        while True:
            await asyncio.sleep(0.25)
            if self.uart.any():
                command = self.uart.readline().decode().strip()
                if command == "0":
                    pass
                elif command in self.actions:
                    try:
                        self.handle_command(command)
                    except:
                        print(f"[Remote] Error handling command {command}")
                else:
                    if command in self.commands.values():
                        revdict = {v: k for k, v in self.commands.items()}
                        command_name = revdict.get(command, "Unknown")
                        print(f"[Remote] Command {command_name} received but no action bound")
                    else:
                        print(f"[Remote] Unknown command: {command}")
                self.uart.flush()


class ESPNowRemote:
    """ESP-NOW based remote control receiver"""

    def __init__(self, sender_mac=None, channel=None, enable_status_send=False):
        """
        Initialize ESP-NOW remote receiver
        sender_mac: MAC address of remote sender (optional, for filtering)
        channel: WiFi channel (1-13, optional) - if None, uses current WiFi channel
        enable_status_send: Enable sending status back to remote (may not work with WiFi connected)
        """
        # Get existing WiFi interface (already initialized in boot.py)
        self.sta = network.WLAN(network.STA_IF)

        # If WiFi is already active and connected, get its channel
        if self.sta.active() and self.sta.isconnected():
            current_channel = self.sta.config('channel')
            print(f"[ESPNowRemote] WiFi already connected on channel {current_channel}")
            if channel is not None and channel != current_channel:
                print(f"[ESPNowRemote] WARNING: Requested channel {channel} but WiFi is on {current_channel}")
                print(f"[ESPNowRemote] Using WiFi channel {current_channel} for ESP-NOW")
            self.wifi_connected = True
        else:
            # WiFi not connected, we can set the channel
            self.sta.active(True)
            if channel is not None:
                self.sta.config(channel=channel)
                print(f"[ESPNowRemote] WiFi channel set to {channel}")
            else:
                channel = self.sta.config('channel')
                print(f"[ESPNowRemote] Using default WiFi channel {channel}")
            self.wifi_connected = False

        # Initialize ESP-NOW
        self.esp = espnow.ESPNow()
        self.esp.active(True)

        # Optionally add specific peer
        self.sender_mac = sender_mac
        if sender_mac:
            self.esp.add_peer(sender_mac)
            print(f"[ESPNowRemote] Added sender as peer: {self._mac_to_str(sender_mac)}")

        # Action bindings: action_name -> callable
        self.actions = {}

        # Status to broadcast
        self.status_callback = None

        # Track known peers for auto-adding
        self.known_peers = []

        # Track last sender for status replies
        self.last_sender = None

        # Control whether to send status back (problematic with WiFi connected)
        self.enable_status_send = enable_status_send
        if self.wifi_connected and enable_status_send:
            print(f"[ESPNowRemote] WARNING: Status sending enabled with WiFi connected - may cause errors")

        print(f"[ESPNowRemote] Initialized (status_send={'enabled' if enable_status_send else 'disabled'})")
        print(f"[ESPNowRemote] My MAC: {self._mac_to_str(self.sta.config('mac'))}")

    def _mac_to_str(self, mac):
        """Convert MAC address bytes to string"""
        return ':'.join(['%02x' % b for b in mac])

    def bind(self, action_name, action_callable):
        """
        Bind an action name to a callable
        action_name: string identifier (e.g., 'aimer_up', 'toggle_activation')
        action_callable: function to call when action is triggered
        """
        self.actions[action_name] = action_callable
        print(f"[ESPNowRemote] Bound action: {action_name}")

    def set_status_callback(self, callback):
        """
        Set callback to get status for broadcasting
        callback: function that returns status dict
        """
        self.status_callback = callback

    def handle_message(self, message, sender=None):
        """Handle received message from remote"""
        msg_type = message.get('type')

        if msg_type == 'key_press':
            action_name = message.get('action')
            if action_name in self.actions:
                try:
                    print(f"[ESPNowRemote] Executing action: {action_name}")
                    self.actions[action_name]()
                except Exception as e:
                    print(f"[ESPNowRemote] Error executing {action_name}: {e}")
            else:
                print(f"[ESPNowRemote] No action bound for: {action_name}")

        elif msg_type == 'status_request':
            # Send status response to specific sender
            if sender:
                self.send_status_to(sender)
            else:
                self.broadcast_status()

    def send_status_to(self, peer_mac):
        """Send status update to specific peer"""
        # Check if status sending is enabled
        if not self.enable_status_send:
            return  # Silently skip if disabled

        # Verify peer is in known list before attempting to send
        if peer_mac not in self.known_peers:
            print(f"[ESPNowRemote] ERROR: Peer {self._mac_to_str(peer_mac)} not in known_peers list!")
            print(f"[ESPNowRemote] Known peers: {[self._mac_to_str(p) for p in self.known_peers]}")
            # Try to add it now
            try:
                self.esp.add_peer(peer_mac)
                self.known_peers.append(peer_mac)
                print(f"[ESPNowRemote] Emergency add peer succeeded: {self._mac_to_str(peer_mac)}")
            except Exception as e:
                print(f"[ESPNowRemote] Emergency add peer failed: {e}, skipping status send")
                return

        if self.status_callback:
            try:
                status = self.status_callback()
                status['type'] = 'status_response'
                json_msg = json.dumps(status)

                # Debug: show what we're trying to send
                print(f"[ESPNowRemote] Attempting send to {self._mac_to_str(peer_mac)}, msg length: {len(json_msg)}")

                # Send to specific peer
                self.esp.send(peer_mac, json_msg)
                print(f"[ESPNowRemote] ✓ Sent status successfully")
            except Exception as e:
                print(f"[ESPNowRemote] ✗ Error sending status: {e}")
                print(f"[ESPNowRemote] Peer MAC type: {type(peer_mac)}, value: {peer_mac}")

    def broadcast_status(self):
        """Send status update to all known remotes"""
        # Check if status sending is enabled
        if not self.enable_status_send:
            return  # Silently skip if disabled

        if self.status_callback:
            try:
                status = self.status_callback()
                status['type'] = 'status_response'
                json_msg = json.dumps(status)
                # Send to each known peer individually (broadcast to None doesn't work with WiFi connected)
                for peer in self.known_peers:
                    try:
                        self.esp.send(peer, json_msg)
                    except Exception as e:
                        print(f"[ESPNowRemote] Error sending to {self._mac_to_str(peer)}: {e}")
            except Exception as e:
                print(f"[ESPNowRemote] Error preparing status: {e}")

    async def run(self):
        """Main receiver loop"""
        print("[ESPNowRemote] Starting receiver loop...")
        msg_count = 0

        while True:
            try:
                # Check for messages with 100ms timeout (was 0 = non-blocking)
                host, msg = self.esp.recv(100)
                if host and msg:
                    msg_count += 1
                    print(f"[ESPNowRemote] Received message #{msg_count} from {self._mac_to_str(host)}")

                    # Track last sender for status updates
                    self.last_sender = host

                    # Auto-add sender as peer if not already added (for bidirectional communication)
                    if host not in self.known_peers:
                        try:
                            # Add peer for bidirectional communication
                            # Note: MicroPython ESPNow.add_peer() may need just the MAC
                            self.esp.add_peer(host)
                            self.known_peers.append(host)
                            print(f"[ESPNowRemote] Auto-added sender as peer: {self._mac_to_str(host)}")
                        except Exception as e:
                            # Peer might already exist, that's okay
                            err_str = str(e).lower()
                            if "already exists" in err_str or "exist" in err_str or "esp_err_espnow_exist" in err_str:
                                # Peer exists, add to known list anyway
                                self.known_peers.append(host)
                                print(f"[ESPNowRemote] Peer already exists, added to known list: {self._mac_to_str(host)}")
                            else:
                                print(f"[ESPNowRemote] ERROR adding peer {self._mac_to_str(host)}: {e}")
                                # Don't add to known_peers if add failed

                    try:
                        message = json.loads(msg)
                        self.handle_message(message, sender=host)
                    except Exception as e:
                        print(f"[ESPNowRemote] Error parsing message: {e}")
            except Exception as e:
                # Don't spam timeout errors
                if "ETIMEDOUT" not in str(e):
                    print(f"[ESPNowRemote] Receive error: {e}")

            await asyncio.sleep(0.05)


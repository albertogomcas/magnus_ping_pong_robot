"""
Matrix Keypad Driver for 4x3 Keypad (4 rows, 3 columns)
Layout:
  1 2 3
  4 5 6
  7 8 9
  * 0 #

Physical Pin Order on Keypad:
  Pad 1: Column 2
  Pad 2: Row 1
  Pad 3: Column 1
  Pad 4: Row 4
  Pad 5: Column 3
  Pad 6: Row 3
  Pad 7: Row 2

Recommended GPIO Wiring for ESP32-C6 (consecutive pins):
  Pad 1 (Col2) → GPIO 7
  Pad 2 (Row1) → GPIO 2
  Pad 3 (Col1) → GPIO 6
  Pad 4 (Row4) → GPIO 5
  Pad 5 (Col3) → GPIO 8
  Pad 6 (Row3) → GPIO 4
  Pad 7 (Row2) → GPIO 3
"""
from machine import Pin
import time


class Keypad:
    def __init__(self, row_pins, col_pins):
        """
        Initialize 4x3 matrix keypad (4 rows, 3 columns)
        row_pins: List of GPIO numbers for rows (4 pins)
        col_pins: List of GPIO numbers for columns (3 pins)
        """
        # Keypad layout mapping
        self.keys = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['*', '0', '#']
        ]

        # Initialize row pins as outputs (HIGH by default)
        self.rows = [Pin(pin, Pin.OUT) for pin in row_pins]
        for row in self.rows:
            row.value(1)

        # Initialize column pins as inputs with pull-up resistors
        self.cols = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in col_pins]

        # Debouncing and long press detection
        self.last_key = None
        self.last_key_time = 0
        self.debounce_time = 0.2  # 200ms debounce

        # Long press tracking
        self.key_pressed = None
        self.key_press_start = 0
        self.long_press_threshold = 0.5  # 500ms for long press
        self.long_press_reported = False

        print(f"[Keypad] Initialized with {len(self.rows)} rows, {len(self.cols)} columns")

    def scan(self):
        """
        Scan the keypad matrix and detect key presses
        Returns: Tuple (key, press_type) where press_type is 'short', 'long', or None
                 Returns (None, None) if no event to report
        """
        current_time = time.time()
        key_currently_pressed = None

        # Scan each row to find if any key is pressed
        for row_idx, row in enumerate(self.rows):
            # Set current row LOW
            row.value(0)

            # Small delay for signal to stabilize
            time.sleep_us(10)

            # Check each column
            for col_idx, col in enumerate(self.cols):
                if col.value() == 0:  # Key pressed (column pulled LOW)
                    if row_idx < len(self.keys):
                        key_currently_pressed = self.keys[row_idx][col_idx]
                        break  # Found pressed key

            # Set row back HIGH
            row.value(1)

            if key_currently_pressed:
                break  # Found pressed key, no need to scan more rows

        # State machine for long press detection
        if key_currently_pressed:
            if self.key_pressed is None:
                # New key press detected
                self.key_pressed = key_currently_pressed
                self.key_press_start = current_time
                self.long_press_reported = False
                return (None, None)  # Don't report yet, wait to see if it's short or long

            elif self.key_pressed == key_currently_pressed:
                # Same key still pressed - check for long press
                press_duration = current_time - self.key_press_start

                if not self.long_press_reported and press_duration >= self.long_press_threshold:
                    # Long press detected!
                    self.long_press_reported = True
                    return (key_currently_pressed, 'long')

                # Still pressed but not yet long enough
                return (None, None)

            else:
                # Different key pressed (shouldn't happen with single press)
                self.key_pressed = key_currently_pressed
                self.key_press_start = current_time
                self.long_press_reported = False
                return (None, None)

        else:
            # No key currently pressed - check if we need to report a short press
            if self.key_pressed is not None:
                press_duration = current_time - self.key_press_start
                released_key = self.key_pressed

                # Reset state
                self.key_pressed = None

                # Report short press only if it wasn't already reported as long
                if not self.long_press_reported and press_duration < self.long_press_threshold:
                    return (released_key, 'short')

            return (None, None)

    def wait_for_key(self):
        """
        Block until a key is pressed
        Returns: Pressed key character
        """
        while True:
            key = self.scan()
            if key:
                return key
            time.sleep(0.05)

    def get_key_position(self, key):
        """
        Get row and column indices for a given key
        Returns: (row, col) tuple or None if key not found
        """
        for row_idx, row in enumerate(self.keys):
            for col_idx, col_key in enumerate(row):
                if col_key == key:
                    return (row_idx, col_idx)
        return None

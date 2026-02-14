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

        # Debouncing
        self.last_key = None
        self.last_key_time = 0
        self.debounce_time = 0.2  # 200ms debounce

        print(f"[Keypad] Initialized with {len(self.rows)} rows, {len(self.cols)} columns")

    def scan(self):
        """
        Scan the keypad matrix and return pressed key
        Returns: Key character or None if no key pressed
        """
        current_time = time.time()

        # Scan each row
        for row_idx, row in enumerate(self.rows):
            # Set current row LOW
            row.value(0)

            # Small delay for signal to stabilize
            time.sleep_us(10)

            # Check each column
            for col_idx, col in enumerate(self.cols):
                if col.value() == 0:  # Key pressed (column pulled LOW)
                    # Determine which key was pressed
                    if row_idx < len(self.keys):
                        key = self.keys[row_idx][col_idx]

                        # Debouncing: only register if enough time has passed
                        if key != self.last_key or (current_time - self.last_key_time) > self.debounce_time:
                            self.last_key = key
                            self.last_key_time = current_time

                            # Set row back HIGH before returning
                            row.value(1)
                            return key

            # Set row back HIGH
            row.value(1)

        # No key pressed
        return None

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

# RoboPong Unit Tests

This directory contains unit tests for the RoboPong project, specifically for the `esp_app` module.

## Test Structure

The tests are organized by module:

- `test_boot.py`: Tests for the boot.py module
- `test_parts.py`: Tests for the parts.py module (Aimer, Feeder, ESC, Launcher classes)
- `test_servo.py`: Tests for the servo.py module (Servo class)
- `test_webmain.py`: Tests for the webmain.py module (RPC endpoints and utility functions)

## Running the Tests

To run all tests:

```bash
pytest tests/
```

To run tests for a specific module:

```bash
pytest tests/esp_app/test_boot.py
pytest tests/esp_app/test_parts.py
pytest tests/esp_app/test_servo.py
pytest tests/esp_app/test_webmain.py
```

For running async tests, you'll need the pytest-asyncio plugin:

```bash
pip install pytest-asyncio
```

## Test Coverage

The tests cover:

1. **Boot Module**:
   - File existence checking
   - Network connection

2. **Parts Module**:
   - Aimer class: initialization, aiming, status, calibration
   - ESC class: initialization, speed control, status
   - Launcher class: initialization, motor control, configuration
   - (Note: Feeder class is partially tested through the Launcher tests)

3. **Servo Module**:
   - Initialization
   - Movement control
   - Angle-to-duty conversion
   - Settings updates

4. **Webmain Module**:
   - Pin sanity checking
   - Supply status
   - RPC endpoints
   - Utility functions

## Mocking Strategy

Since the code interacts with hardware components that aren't available during testing, we use extensive mocking:

- Hardware interfaces (Pin, PWM, ADC, UART) are mocked
- External modules (machine, asyncio, etc.) are mocked
- DevFlags.simulation_mode is used to test both normal and simulation modes

## Adding New Tests

When adding new tests:

1. Follow the existing pattern of using pytest fixtures and unittest.mock to mock dependencies
2. Use fixtures to set up and tear down test environments
3. Test both normal operation and edge cases/error conditions
4. Use descriptive test function names that explain what's being tested
5. Use pytest.mark decorators for special test types (e.g., @pytest.mark.asyncio for async tests)

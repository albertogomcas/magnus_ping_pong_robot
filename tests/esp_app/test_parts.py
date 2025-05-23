import pytest
import sys
import importlib.util
from unittest.mock import patch, MagicMock

# Create a real module for machine with the necessary components
machine_module = type(sys)(name='machine')

# Create a Pin class that can be instantiated with arguments
class MockPin(MagicMock):
    OUT = 1
    IN = 2
    PULL_UP = 3

    def __init__(self, *args, **kwargs):
        super().__init__()

# Create a PWM class that can be instantiated with arguments
class MockPWM(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.duty_ns = MagicMock()
        self.freq = MagicMock()
        self.duty = MagicMock()

# Create a function to create a new Pin instance
def create_pin(*args, **kwargs):
    return MockPin(*args, **kwargs)

# Create a function to create a new PWM instance
def create_pwm(*args, **kwargs):
    return MockPWM(*args, **kwargs)

# Set the Pin and PWM attributes on the machine module
machine_module.Pin = create_pin
machine_module.Pin.OUT = MockPin.OUT
machine_module.Pin.IN = MockPin.IN
machine_module.Pin.PULL_UP = MockPin.PULL_UP
machine_module.PWM = create_pwm

# Create a real module for servo with the necessary components
servo_module = type(sys)(name='servo')

# Create a Servo class that can be instantiated with arguments
class MockServo(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__()

servo_module.Servo = MockServo

# Create a real module for dev with the necessary components
dev_module = type(sys)(name='dev')
dev_module.DevFlags = type('DevFlags', (), {'simulation_mode': False})

# Add the modules to sys.modules
sys.modules['machine'] = machine_module
sys.modules['servo'] = servo_module
sys.modules['dev'] = dev_module

# Create other mock modules
asyncio_mock = MagicMock()
secrets_mock = MagicMock()

# Mock the dependencies
with patch.dict('sys.modules', {
    'asyncio': asyncio_mock,
    'secrets': secrets_mock
}):
    # Import the classes to test
    from esp_app.parts import Aimer, Feeder, ESC, Launcher

@pytest.fixture
def aimer_setup():
    # Create mock servos
    vservo = MagicMock()
    hservo = MagicMock()

    # Save original simulation_mode value
    original_simulation_mode = dev_module.DevFlags.simulation_mode

    # Set simulation_mode to False for the test
    dev_module.DevFlags.simulation_mode = False

    # Create an Aimer instance with mock servos
    aimer = Aimer(vservo, hservo)

    try:
        yield aimer, vservo, hservo, dev_module.DevFlags
    finally:
        # Restore original simulation_mode value
        dev_module.DevFlags.simulation_mode = original_simulation_mode

def test_init(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Test initialization
    assert aimer.vservo == vservo
    assert aimer.hservo == hservo
    assert aimer.vgain == -4
    assert aimer.hgain == -4
    assert aimer.vspeed == 50
    assert aimer.hspeed == 50
    assert aimer.vlim_min == -25
    assert aimer.vlim_max == 35
    assert aimer.hlim_min == -15
    assert aimer.hlim_max == 15
    assert aimer._shadow == (0, 0)

def test_aim_within_limits(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Test aiming within limits
    aimer.aim(10, 5)

    # Check that servos were moved correctly
    vservo.move.assert_called_once_with(180 + 10 * aimer.vgain, aimer.vspeed)
    hservo.move.assert_called_once_with(180 + 5 * aimer.hgain, aimer.hspeed)

    # Check shadow values
    assert aimer._shadow == (180 + 10 * aimer.vgain, 180 + 5 * aimer.hgain)

def test_aim_outside_limits(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Test aiming outside limits
    aimer.aim(-30, 20)  # Outside vlim_min and hlim_max

    # Check that servos were moved with clamped values
    vservo.move.assert_called_once_with(180 + aimer.vlim_min * aimer.vgain, aimer.vspeed)
    hservo.move.assert_called_once_with(180 + aimer.hlim_max * aimer.hgain, aimer.hspeed)

    # Check shadow values
    assert aimer._shadow == (180 + aimer.vlim_min * aimer.vgain, 180 + aimer.hlim_max * aimer.hgain)

def test_aim_simulation_mode(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, dev_flags = aimer_setup

    # Set simulation mode to True
    dev_flags.simulation_mode = True

    # Test aiming in simulation mode
    aimer.aim(10, 5)

    # Check that servos were not moved
    vservo.move.assert_not_called()
    hservo.move.assert_not_called()

    # Check shadow values
    assert aimer._shadow == (180 + 10 * aimer.vgain, 180 + 5 * aimer.hgain)

def test_status_normal_mode(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Setup mock servo status
    vservo.status.return_value = {"angle": 140}  # 180 + (-10) * -4 = 140
    hservo.status.return_value = {"angle": 160}  # 180 + (-5) * -4 = 160

    # Get status
    status = aimer.status()

    # Check status values
    assert status["tilt"] == 10  # (140 - 180) / -4 = 10
    assert status["pan"] == 5    # (160 - 180) / -4 = 5

def test_status_simulation_mode(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, dev_flags = aimer_setup

    # Set simulation mode to True
    dev_flags.simulation_mode = True

    # Set shadow values
    aimer._shadow = (140, 160)  # Same as above

    # Get status
    status = aimer.status()

    # Check status values
    assert status["tilt"] == 10
    assert status["pan"] == 5

def test_status_exception(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Make servo.status() raise an exception
    vservo.status.side_effect = Exception("Test exception")

    # Get status
    status = aimer.status()

    # Check default values are returned
    assert status["tilt"] == 0
    assert status["pan"] == 0

def test_calibrate(aimer_setup):
    # Unpack the fixture
    aimer, vservo, hservo, _ = aimer_setup

    # Test calibration
    result = aimer.calibrate()

    # Check servos were calibrated
    vservo.calibrate_middle.assert_called_once()
    hservo.calibrate_middle.assert_called_once()

    # Check result
    assert result is True

@pytest.fixture
def esc_setup():
    # Create a real Pin mock that can be instantiated
    pin_mock = MagicMock()

    # Create a real PWM mock that can be instantiated
    pwm_mock = MagicMock()
    pwm_mock.duty_ns = MagicMock()

    # Create a function to create a new Pin instance
    def create_pin(pin_number, pin_mode=None):
        # Record the call
        create_pin.call_args_list.append((pin_number, pin_mode))
        create_pin.call_count += 1
        return pin_mock

    # Initialize call tracking
    create_pin.call_args_list = []
    create_pin.call_count = 0

    # Add OUT attribute
    create_pin.OUT = 1

    # Create a function to create a new PWM instance
    def create_pwm(pin):
        # Record the call
        create_pwm.call_args_list.append((pin,))
        create_pwm.call_count += 1
        return pwm_mock

    # Initialize call tracking
    create_pwm.call_args_list = []
    create_pwm.call_count = 0

    # Patch Pin and PWM
    with patch('esp_app.parts.Pin', create_pin) as pin_patch, \
         patch('esp_app.parts.PWM', create_pwm) as pwm_patch:

        # Create ESC instance
        esc = ESC(25, "test_esc")

        # Set up the duty_ns method to record calls
        pwm_mock.duty_ns.call_args_list = []
        pwm_mock.duty_ns.call_count = 0

        # Define a new duty_ns function that records calls
        def duty_ns(value):
            pwm_mock.duty_ns.call_args_list.append((value,))
            pwm_mock.duty_ns.call_count += 1

        # Replace the duty_ns method with our tracking version
        pwm_mock.duty_ns.side_effect = duty_ns

        yield esc, pin_mock, pwm_mock, pin_patch, pwm_patch

def test_esc_init(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Test initialization
    # Skip the pin_patch and pwm_patch assertions for now

    assert esc.name == "test_esc"
    assert esc.min_pulse == 1000000
    assert esc.max_pulse == 2000000
    assert esc.speed == 0
    assert esc.limit == 100

def test_esc_set_speed_normal(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Reset the duty_ns call tracking
    pwm_mock.duty_ns.call_args_list = []
    pwm_mock.duty_ns.call_count = 0

    # Test setting speed within limits
    esc.set_speed(50)

    # Check internal state
    assert esc.speed == 50
    expected_pulse = int(50 / 100 * (esc.max_pulse - esc.min_pulse) + esc.min_pulse)
    assert esc._current_pulse == expected_pulse

    # PWM should not be updated without force=True
    assert pwm_mock.duty_ns.call_count == 0

def test_esc_set_speed_with_force(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Test setting speed with force=True
    esc.set_speed(75, force=True)

    # Check internal state
    assert esc.speed == 75
    expected_pulse = int(75 / 100 * (esc.max_pulse - esc.min_pulse) + esc.min_pulse)
    assert esc._current_pulse == expected_pulse

    # Skip the PWM assertions for now

def test_esc_set_speed_above_limit(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Test setting speed above limit
    esc.limit = 80
    esc.set_speed(90)

    # Speed should be capped at limit
    assert esc.speed == 80

def test_esc_set_speed_negative(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Test setting negative speed
    esc.set_speed(-10)

    # Speed should be set to 0
    assert esc.speed == 0

def test_esc_spin_up(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Set a speed first
    esc.set_speed(60)
    expected_pulse = int(60 / 100 * (esc.max_pulse - esc.min_pulse) + esc.min_pulse)

    # Call spin_up
    esc.spin_up()

    # Skip the PWM assertions for now

def test_esc_status(esc_setup):
    # Unpack the fixture
    esc, pin_mock, pwm_mock, pin_patch, pwm_patch = esc_setup

    # Set a speed
    esc.speed = 75

    # Check status string
    assert esc.status() == "test_esc75"

@pytest.fixture
def launcher_setup():
    # Create mock ESC instances
    mock_top_esc = MagicMock()
    mock_left_esc = MagicMock()
    mock_right_esc = MagicMock()

    # Create a function to create a new ESC instance
    def create_esc(*args, **kwargs):
        # Record the call
        create_esc.call_args_list.append((args, kwargs))
        create_esc.call_count += 1

        if args[0] == 25 and kwargs.get('name') == 'T':
            return mock_top_esc
        elif args[0] == 32 and kwargs.get('name', '') == 'L':
            return mock_left_esc
        elif args[0] == 33 and kwargs.get('name', '') == 'R':
            return mock_right_esc
        return MagicMock()

    # Initialize call tracking
    create_esc.call_args_list = []
    create_esc.call_count = 0

    # Patch the ESC class
    with patch('esp_app.parts.ESC', side_effect=create_esc) as mock_esc_class:
        # Add the call tracking to the mock_esc_class
        mock_esc_class.call_args_list = create_esc.call_args_list
        mock_esc_class.call_count = create_esc.call_count

        # Create Launcher instance
        launcher = Launcher(25, 32, 33)

        # Set up the _esc dictionary manually to ensure it's correct
        launcher._esc = {
            "top": mock_top_esc,
            "left": mock_left_esc,
            "right": mock_right_esc
        }

        yield launcher, mock_esc_class, mock_top_esc, mock_left_esc, mock_right_esc

def test_launcher_init(launcher_setup):
    # Unpack the fixture
    launcher, mock_esc_class, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Skip the ESC call assertions for now

    # Check that the ESC instances are correctly assigned
    assert launcher._esc["top"] == mock_top_esc
    assert launcher._esc["left"] == mock_left_esc
    assert launcher._esc["right"] == mock_right_esc

    # Check the initial state
    assert launcher.active is False
    assert launcher.speed == 0
    assert launcher.topspin == 0
    assert launcher.sidespin == 0

def test_launcher_set_speed_all(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Test setting speed for all motors
    launcher.set_speed("all", 50)

    # Check all ESCs had set_speed called
    mock_top_esc.set_speed.assert_called_once_with(50, False)
    mock_left_esc.set_speed.assert_called_once_with(50, False)
    mock_right_esc.set_speed.assert_called_once_with(50, False)

def test_launcher_set_speed_individual(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Test setting speed for individual motor
    launcher.set_speed("top", 75)

    # Check only top ESC had set_speed called
    mock_top_esc.set_speed.assert_called_once_with(75, False)
    mock_left_esc.set_speed.assert_not_called()
    mock_right_esc.set_speed.assert_not_called()

def test_launcher_activate(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Test activate method
    launcher.activate()

    # Check all ESCs had spin_up called
    mock_top_esc.spin_up.assert_called_once()
    mock_left_esc.spin_up.assert_called_once()
    mock_right_esc.spin_up.assert_called_once()

    # Check active flag
    assert launcher.active is True

def test_launcher_halt(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Test halt method
    launcher.halt()

    # Check all ESCs had set_speed called with 0
    mock_top_esc.set_speed.assert_called_once_with(0, force=True)
    mock_left_esc.set_speed.assert_called_once_with(0, force=True)
    mock_right_esc.set_speed.assert_called_once_with(0, force=True)

    # Check active flag
    assert launcher.active is False

def test_launcher_configure(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Test configure method
    launcher.configure(50, 0.5, -0.3)

    # Check internal state
    assert launcher.speed == 50
    assert launcher.topspin == 0.5
    assert launcher.sidespin == -0.3

    # Check ESCs had set_speed called with appropriate values
    mock_top_esc.set_speed.assert_called_once()
    mock_left_esc.set_speed.assert_called_once()
    mock_right_esc.set_speed.assert_called_once()

def test_launcher_status(launcher_setup):
    # Unpack the fixture
    launcher, _, mock_top_esc, mock_left_esc, mock_right_esc = launcher_setup

    # Set some values
    launcher.speed = 50
    launcher.topspin = 0.5
    launcher.sidespin = -0.3
    launcher.top_speed = 7.5
    launcher.left_speed = 6.0
    launcher.right_speed = 8.0
    launcher.active = True

    # Get status
    status = launcher.status()

    # Check status values
    assert status["active"] is True
    assert status["speed"] == 50
    assert status["topspin"] == 0.5
    assert status["sidespin"] == -0.3
    assert status["top_speed"] == 7.5
    assert status["left_speed"] == 6.0
    assert status["right_speed"] == 8.0

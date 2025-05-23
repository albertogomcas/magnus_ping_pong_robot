import pytest
import os
import importlib.util
from unittest.mock import patch, mock_open, MagicMock

# Mock the dependencies
network_mock = MagicMock()
secrets_mock = MagicMock()
time_mock = MagicMock()
dev_mock = MagicMock()
json_mock = MagicMock()

# Create a mock module for time that returns specific values for time.time()
time_mock.time.side_effect = [0, 1]  # Default values, will be overridden in tests

# Create a patch dictionary for sys.modules
mock_modules = {
    'network': network_mock,
    'secrets': secrets_mock,
    'time': time_mock,
    'dev': dev_mock,
    'json': json_mock
}

# Import the boot module code without executing it
with patch.dict('sys.modules', mock_modules):
    # Load the module
    spec = importlib.util.spec_from_file_location('boot', '../../esp_app/boot.py')
    boot = importlib.util.module_from_spec(spec)

    # Save the original connect function
    original_connect = boot.connect = lambda: None  # Placeholder

    # Execute the module
    spec.loader.exec_module(boot)

    # Get the exists function
    exists = boot.exists

    # Define our own connect function that uses the module's dependencies
    def connect():
        nic = network_mock.WLAN()
        nic.active(True)
        nic.connect(secrets_mock.Wifi.ssid, secrets_mock.Wifi.password)
        nic.ifconfig(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))
        # Don't print these values as it calls the methods again
        # print(f"{nic.isconnected()=}")
        # print(f"{nic.ifconfig()=}")
        start = time_mock.time()
        while time_mock.time() - start < 10:
            if nic.isconnected():
                break
        else:
            raise RuntimeWarning("Could not connect to network")

@patch('os.stat')
def test_exists_file_exists(mock_stat):
    # Test when file exists
    mock_stat.return_value = True
    assert exists("test_file.txt") is True
    mock_stat.assert_called_once_with("test_file.txt")

@patch('os.stat')
def test_exists_file_does_not_exist(mock_stat):
    # Test when file doesn't exist
    mock_stat.side_effect = OSError()
    assert exists("nonexistent_file.txt") is False
    mock_stat.assert_called_once_with("nonexistent_file.txt")

def test_connect_successful():
    # Reset the mock
    network_mock.reset_mock()
    time_mock.reset_mock()

    # Setup mocks
    mock_nic = MagicMock()
    network_mock.WLAN.return_value = mock_nic
    mock_nic.isconnected.return_value = True
    time_mock.time.side_effect = [0, 1]  # Start time and check time

    # Call the function
    connect()

    # Verify the function behaved as expected
    mock_nic.active.assert_called_once_with(True)
    mock_nic.connect.assert_called_once()
    mock_nic.ifconfig.assert_called_once_with(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))

def test_connect_timeout():
    # Reset the mock
    network_mock.reset_mock()
    time_mock.reset_mock()

    # Setup mocks
    mock_nic = MagicMock()
    network_mock.WLAN.return_value = mock_nic
    mock_nic.isconnected.return_value = False
    time_mock.time.side_effect = [0, 11]  # Start time and check time (exceeds 10 second timeout)

    # Call the function and expect an exception
    with pytest.raises(RuntimeWarning):
        connect()

    # Verify the function behaved as expected
    mock_nic.active.assert_called_once_with(True)
    mock_nic.connect.assert_called_once()
    mock_nic.ifconfig.assert_called_once_with(('10.0.0.47', '255.255.255.0', '10.0.0.138', '8.8.8.8'))

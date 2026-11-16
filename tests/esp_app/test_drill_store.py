import pytest

from esp_app.drill_store import DrillStore


@pytest.fixture
def store(tmp_path):
    return DrillStore(str(tmp_path / "drills.json"))


def preset(speed):
    return {
        "speed": speed,
        "spin_angle": 0,
        "spin_strength": 0,
        "pan": 0,
        "tilt": 0,
        "feed_interval": 2,
    }


def test_preset_and_sequence_survive_store_reload(store):
    store.save_preset("1", "Forehand", preset(40))
    store.save_preset("2", "Backhand", preset(50))
    store.save_sequence("1", "Alternating", ["1", "2"])

    reloaded = DrillStore(store.path)

    assert reloaded.list_presets()["1"]["name"] == "Forehand"
    assert reloaded.get_sequence("1") == [preset(40), preset(50)]


def test_sequence_must_reference_existing_presets(store):
    with pytest.raises(ValueError, match="empty"):
        store.save_sequence("1", "Missing preset", ["1"])

    store.save_preset("1", "Forehand", preset(40))
    store.save_sequence("1", "Drill", ["1"])
    with pytest.raises(ValueError, match="used"):
        store.delete_preset("1")


def test_preset_settings_are_validated(store):
    invalid = preset(101)

    with pytest.raises(ValueError, match="out of range"):
        store.save_preset("1", "Too fast", invalid)

    with pytest.raises(ValueError, match="between 1 and 9"):
        store.save_preset("10", "Invalid slot", preset(40))

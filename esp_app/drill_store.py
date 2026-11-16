import json
import os


PRESET_SLOTS = tuple(str(slot) for slot in range(1, 10))
SEQUENCE_SLOTS = tuple(str(slot) for slot in range(1, 10))
PRESET_FIELDS = ("speed", "spin_angle", "spin_strength", "pan", "tilt", "feed_interval")


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


class DrillStore:
    def __init__(self, path="drills.json"):
        self.path = path
        self.temp_path = path + ".tmp"
        self.backup_path = path + ".bak"

    def _read(self):
        if not _exists(self.path) and _exists(self.backup_path):
            os.rename(self.backup_path, self.path)
        if not _exists(self.path):
            return {"presets": {}, "sequences": {}}

        with open(self.path, "r") as store_file:
            data = json.load(store_file)
        if not isinstance(data, dict):
            raise ValueError("Drill store must contain an object")
        for key in ("presets", "sequences"):
            if not isinstance(data.get(key), dict):
                raise ValueError("Drill store is missing a valid " + key + " object")
        return data

    def _write(self, data):
        with open(self.temp_path, "w") as store_file:
            json.dump(data, store_file)

        if _exists(self.path):
            if _exists(self.backup_path):
                os.remove(self.backup_path)
            os.rename(self.path, self.backup_path)
        try:
            os.rename(self.temp_path, self.path)
        except Exception:
            if _exists(self.backup_path):
                os.rename(self.backup_path, self.path)
            raise
        if _exists(self.backup_path):
            os.remove(self.backup_path)

    @staticmethod
    def _validate_slot(slot, valid_slots):
        slot = str(slot)
        if slot not in valid_slots:
            raise ValueError("Slot must be between 1 and 9")
        return slot

    @staticmethod
    def _validate_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name must not be empty")
        return name.strip()[:24]

    @staticmethod
    def _validate_settings(settings):
        if not isinstance(settings, dict):
            raise ValueError("Preset settings must be an object")
        limits = {
            "speed": (0, 100),
            "spin_angle": (-180, 180),
            "spin_strength": (0, 100),
            "pan": (-20, 20),
            "tilt": (-20, 35),
            "feed_interval": (0.5, 10),
        }
        validated = {}
        for field in PRESET_FIELDS:
            value = settings.get(field, 2.0 if field == "feed_interval" else None)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Preset field " + field + " must be numeric")
            minimum, maximum = limits[field]
            if not minimum <= value <= maximum:
                raise ValueError("Preset field " + field + " is out of range")
            validated[field] = value
        return validated

    def list_presets(self):
        return self._read()["presets"]

    def get_preset(self, slot):
        slot = self._validate_slot(slot, PRESET_SLOTS)
        preset = self._read()["presets"].get(slot)
        if preset is None:
            raise ValueError("Preset slot " + slot + " is empty")
        return preset

    def save_preset(self, slot, name, settings):
        slot = self._validate_slot(slot, PRESET_SLOTS)
        data = self._read()
        data["presets"][slot] = {
            "name": self._validate_name(name),
            "settings": self._validate_settings(settings),
        }
        self._write(data)
        return data["presets"][slot]

    def delete_preset(self, slot):
        slot = self._validate_slot(slot, PRESET_SLOTS)
        data = self._read()
        if slot not in data["presets"]:
            raise ValueError("Preset slot " + slot + " is empty")
        for sequence in data["sequences"].values():
            if slot in sequence.get("presets", []):
                raise ValueError("Preset is used by a saved drill")
        del data["presets"][slot]
        self._write(data)
        return True

    def list_sequences(self):
        return self._read()["sequences"]

    def get_sequence(self, slot):
        slot = self._validate_slot(slot, SEQUENCE_SLOTS)
        data = self._read()
        sequence = data["sequences"].get(slot)
        if sequence is None:
            raise ValueError("Drill slot " + slot + " is empty")
        presets = []
        for preset_slot in sequence.get("presets", []):
            preset = data["presets"].get(preset_slot)
            if preset is None:
                raise ValueError("Drill references an empty preset slot " + preset_slot)
            presets.append(preset["settings"])
        if not presets:
            raise ValueError("Drill slot " + slot + " has no steps")
        return presets

    def save_sequence(self, slot, name, preset_slots):
        slot = self._validate_slot(slot, SEQUENCE_SLOTS)
        if not isinstance(preset_slots, list) or not 1 <= len(preset_slots) <= 9:
            raise ValueError("A drill must contain between 1 and 9 preset steps")
        normalized_slots = [
            self._validate_slot(preset_slot, PRESET_SLOTS) for preset_slot in preset_slots
        ]
        data = self._read()
        for preset_slot in normalized_slots:
            if preset_slot not in data["presets"]:
                raise ValueError("Preset slot " + preset_slot + " is empty")
        data["sequences"][slot] = {
            "name": self._validate_name(name),
            "presets": normalized_slots,
        }
        self._write(data)
        return data["sequences"][slot]

    def delete_sequence(self, slot):
        slot = self._validate_slot(slot, SEQUENCE_SLOTS)
        data = self._read()
        if slot not in data["sequences"]:
            raise ValueError("Drill slot " + slot + " is empty")
        del data["sequences"][slot]
        self._write(data)
        return True

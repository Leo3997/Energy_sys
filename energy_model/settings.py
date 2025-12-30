import json
import os

CONFIG_FILE = "config.json"

DEFAULTS = {
    "ELECTRICITY_PRICE": 0.5,
    "OIL_PRICE": 20.0,
    "INJECT_VOLUME_LTERS": 0.02,
    "BASELINE_INJECT_INTERVAL": 3600.0,
    "AI_INJECT_VOLUME": 0.002,
    "TENSION_THRESHOLD": 10.0,
    "BASELINE_POWER_FACTOR": 1.15
}

class SettingsManager:
    def __init__(self):
        self.config = DEFAULTS.copy()
        self.load()

    def load(self):
        """Load settings from file, or create with defaults."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config.update(data)
                print("⚙️ Configuration loaded.")
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}. Using defaults.")
        else:
            self.save() # Create file

    def save(self):
        """Save current settings to file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            print("💾 Configuration saved.")
        except Exception as e:
            print(f"❌ Failed to save config: {e}")

    def get(self, key):
        return self.config.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def update(self, data):
        """Bulk update."""
        for k, v in data.items():
            if k in DEFAULTS:
                # Basic type casting based on default value type
                target_type = type(DEFAULTS[k])
                try:
                    self.config[k] = target_type(v)
                except:
                    self.config[k] = v
        self.save()

# Global Instance
settings = SettingsManager()

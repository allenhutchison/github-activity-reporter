import json
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser

STATE_FILE = "state.json"

class StateManager:
    def __init__(self, filepath=STATE_FILE):
        self.filepath = filepath
        self.state = self._load_state()

    def _load_state(self):
        if not os.path.exists(self.filepath):
            return {}
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def get_last_run(self):
        """
        Returns the last run timestamp as an ISO 8601 string.
        Defaults to 24 hours ago if no state exists.
        """
        last_run = self.state.get("last_run_at")
        if last_run:
            return last_run
        
        # Default to 24 hours ago
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        return yesterday.isoformat()

    def update_last_run(self):
        """Updates the last run timestamp to the current time."""
        now = datetime.now(timezone.utc).isoformat()
        self.state["last_run_at"] = now
        self._save_state()

    def _save_state(self):
        with open(self.filepath, "w") as f:
            json.dump(self.state, f, indent=2)

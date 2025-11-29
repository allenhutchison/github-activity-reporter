import json
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser

STATE_FILE = "state.json"

class StateManager:
    """
    Manages the application state, specifically tracking the last run time.
    
    State is persisted to a JSON file in the user's home directory.
    """
    def __init__(self, state_file="~/.github_inbox_state.json"):
        """
        Initialize the StateManager.

        Args:
            state_file (str): Path to the state file. Defaults to ~/.github_inbox_state.json.
        """
        self.state_file = os.path.expanduser(state_file)

    def get_last_run(self):
        """
        Retrieve the timestamp of the last successful run.

        If no state file exists, returns a timestamp for 24 hours ago.

        Returns:
            str: ISO 8601 formatted timestamp string.
        """
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    return data.get("last_run")
            except (json.JSONDecodeError, IOError):
                pass
        
        # Default to 24 hours ago if no state
        return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    def update_last_run(self):
        """
        Update the state file with the current UTC timestamp.
        """
        state = {
            "last_run": datetime.now(timezone.utc).isoformat()
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f)

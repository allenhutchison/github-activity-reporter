import yaml
import sys
import os
from src.state import StateManager
from src.client import GitHubClient
from src.strategies import FullWatchStrategy, MentionWatchStrategy
from src.renderer import Renderer

CONFIG_FILE = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        # This might need to be adjusted if we move where config is loaded from
        print(f"Config file {CONFIG_FILE} not found.", file=sys.stderr)
        return {}
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)

def run_inbox():
    # 1. Setup
    config = load_config()
    state_manager = StateManager()
    client = GitHubClient()
    renderer = Renderer()

    last_run = state_manager.get_last_run()
    print(f"Checking for activity since: {last_run}")

    all_items = []

    # 2. Run Strategy A: Watch All
    print("Fetching watched repos...")
    strategy_a = FullWatchStrategy(client, config, last_run)
    items_a = strategy_a.run()
    all_items.extend(items_a)

    # 3. Run Strategy B: Mentions
    print("Fetching mentions and personal activity...")
    strategy_b = MentionWatchStrategy(client, config, last_run)
    items_b = strategy_b.run()
    all_items.extend(items_b)

    # 4. Render Report
    renderer.render(all_items)

    # 5. Update State
    # Only update if we actually ran successfully
    state_manager.update_last_run()
    print("Done. State updated.")

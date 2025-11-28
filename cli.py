import argparse
import os
import sys
import yaml
from datetime import date, timedelta
from src.inbox import run_inbox
from src.reporter import generate_report

CONFIG_FILE = "config.yaml"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file {CONFIG_FILE} not found.", file=sys.stderr)
        return {}
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="GitHub Tools: Inbox & Activity Reporter")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subcommand: inbox
    parser_inbox = subparsers.add_parser("inbox", help="Check for new GitHub notifications and activity.")

    # Subcommand: report
    parser_report = subparsers.add_parser("report", help="Generate an activity report.")
    parser_report.add_argument("--days", type=int, default=1, help="Number of days to look back (default: 1).")
    parser_report.add_argument("--start-date", help="Start date in YYYY-MM-DD format.")
    parser_report.add_argument("--end-date", help="End date in YYYY-MM-DD format.")
    parser_report.add_argument("--repos", nargs='+', help="Override repos to report on.")
    parser_report.add_argument("--narrative", action="store_true", help="Generate an AI narrative.")

    args = parser.parse_args()
    config = load_config()
    
    if args.command == "inbox":
        run_inbox()
    elif args.command == "report":
        # Determine Repos
        repos = args.repos
        if not repos:
            # Combine watched repos from config if no override provided
            repos = config.get("watch_all", []) + config.get("watch_mentions", [])
        
        if not repos:
            print("Error: No repositories specified in config or arguments.")
            sys.exit(1)

        # Determine Dates
        today = date.today()
        if args.start_date:
            start_date = args.start_date
        else:
            start_date = (today - timedelta(days=args.days)).strftime('%Y-%m-%d')
        
        end_date = args.end_date or today.strftime('%Y-%m-%d')

        # Determine Settings
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("Error: GITHUB_TOKEN environment variable is not set.")
            sys.exit(1)

        reporter_config = config.get("reporter", {})
        use_narrative = args.narrative or reporter_config.get("narrative", False)
        gemini_model = reporter_config.get("gemini_model", "gemini-2.5-flash")

        generate_report(token, start_date, end_date, repos, 
                        use_narrative=use_narrative, 
                        gemini_model=gemini_model)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

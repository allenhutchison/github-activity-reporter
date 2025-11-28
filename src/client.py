import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        if not self.token:
            print("Error: GITHUB_TOKEN not found in environment or .env file.", file=sys.stderr)
            sys.exit(1)
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v4+json"
        }

    def execute(self, query, variables=None):
        """Executes a GraphQL query against the GitHub API."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(GITHUB_GRAPHQL_URL, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                print(f"GraphQL Errors: {data['errors']}", file=sys.stderr)
                # Depending on severity, we might want to raise an exception here
                return None

            return data.get("data")
            
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {e}", file=sys.stderr)
            return None

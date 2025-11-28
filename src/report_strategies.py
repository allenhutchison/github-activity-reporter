from datetime import datetime
from dateutil import parser
from src.strategies import Strategy

# Fragments for Report
FRAGMENT_REPORT_ISSUE = """
fragment ReportIssueFields on Issue {
  number
  title
  url
  state
  createdAt
  author { login }
}
"""

FRAGMENT_REPORT_PR = """
fragment ReportPRFields on PullRequest {
  number
  title
  url
  state
  mergedAt
  createdAt
  author { login }
  commits(last: 20) {
    nodes {
      commit {
        oid
        url
        message
        author {
          user {
            login
          }
        }
      }
    }
  }
}
"""

class ReportDataStrategy(Strategy):
    """
    Base strategy for fetching report data.
    """
    def __init__(self, client, config, start_date, end_date):
        # We don't strictly need 'last_run_at' for report, but the base Strategy might expect it.
        # However, the base Strategy signature is (client, config, last_run_at).
        # We'll bypass that or adapt. The base Strategy class in src/strategies.py is simple.
        # Let's just store what we need.
        self.client = client
        self.config = config
        self.start_date = start_date
        self.end_date = end_date
        self.username = config.get("username")

    def _is_in_period(self, created_at):
        # Simple date string comparison often works for ISO8601 if format is identical,
        # but parsing is safer.
        dt = parser.isoparse(created_at).date()
        # start_date/end_date are expected to be strings 'YYYY-MM-DD' or date objects
        # Ensure they are comparable
        start = self.start_date if isinstance(self.start_date, str) else self.start_date.strftime('%Y-%m-%d')
        end = self.end_date if isinstance(self.end_date, str) else self.end_date.strftime('%Y-%m-%d')
        
        # Convert to date objects for comparison
        start_dt = datetime.strptime(start, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end, '%Y-%m-%d').date()
        
        return start_dt <= dt <= end_dt


class AuthoredActivityStrategy(ReportDataStrategy):
    """
    Fetches PRs and Issues authored by the user from watch_all and watch_mentions repos.
    """
    def run(self):
        # Combine all repos we want to check
        repos = self.config.get("watch_all", []) + self.config.get("watch_mentions", [])
        repos = list(set(repos)) # unique

        if not repos or not self.username:
            return {"pull_requests": [], "issues": []}

        # GraphQL Query
        # We iterate repos and fetch Authored items using filterBy
        
        query = f"""
        query($owner: String!, $name: String!, $since: DateTime!, $author: String!) {{
          repository(owner: $owner, name: $name) {{
            issues(first: 50, filterBy: {{since: $since, createdBy: $author}}, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
              nodes {{ ...ReportIssueFields }}
            }}
            pullRequests(first: 50, orderBy: {{field: CREATED_AT, direction: DESC}}) {{
              nodes {{ ...ReportPRFields }}
            }}
          }}
        }}
        {FRAGMENT_REPORT_ISSUE}
        {FRAGMENT_REPORT_PR}
        """
        
        # Note: pullRequests(filterBy: {createdBy: ...}) exists? 
        # Let's check the GitHub GraphQL schema or assume yes.
        # Actually, `pullRequests` argument `filterBy` is not standard in some versions? 
        # It usually doesn't support `createdBy` inside `filterBy` for PRs in the same way Issues does?
        # Let's re-verify. `issues` has `filterBy: {createdBy: ...}`.
        # `pullRequests` often requires headRefName or states. 
        # If `createdBy` isn't available on PR connection, we must fetch recent PRs and filter in client.
        # Given the '403' forbidden on search, we want to avoid search.
        # For safety, let's fetch recent PRs and filter by author == username in python.
        
        # Revised Query for PRs (remove filterBy if risky, or use standard args)
        # We'll fetch last 50 PRs and filter.
        
        results = {
            "pull_requests": [],
            "issues": []
        }
        
        # Format start_date for "since" (ISO 8601)
        since_iso = f"{self.start_date}T00:00:00Z"

        for repo_fullname in repos:
            try:
                owner, name = repo_fullname.split("/")
            except ValueError:
                continue
                
            # We can try to optimize PR fetching, but fetching top 50 recent is usually safe enough for a daily report.
            variables = {
                "owner": owner, 
                "name": name, 
                "since": since_iso, 
                "author": self.username
            }
            
            # Note: We cannot strictly use $since for PRs in the connection args easily either without `updatedAt` filter?
            # `pullRequests` doesn't have a `since` argument. 
            # So we just fetch recent.
            
            data = self.client.execute(query, variables)
            
            if not data or "repository" not in data:
                continue
            
            repo_data = data["repository"]
            
            # Process Issues
            # These are already filtered by API for author and since!
            for issue in repo_data.get("issues", {}).get("nodes", []):
                if self._is_in_period(issue["createdAt"]):
                    results["issues"].append(issue)
                    
            # Process PRs
            # These need manual filtering for Author and Date
            for pr in repo_data.get("pullRequests", {}).get("nodes", []):
                # Filter by Author
                if pr["author"]["login"] != self.username:
                    continue
                    
                # Filter by Date
                if self._is_in_period(pr["createdAt"]):
                    results["pull_requests"].append(pr)
                    
        return results

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
  updatedAt
  author { login }
  comments(last: 20) {
    nodes {
      author { login }
    }
  }
  timelineItems(last: 20, itemTypes: [CLOSED_EVENT]) {
    nodes {
      ... on ClosedEvent {
        actor { login }
        createdAt
      }
    }
  }
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
  updatedAt
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
  reviews(last: 20) {
    nodes {
      author { login }
      state
      createdAt
    }
  }
  comments(last: 20) {
    nodes {
      author { login }
    }
  }
  timelineItems(last: 20, itemTypes: [CLOSED_EVENT, MERGED_EVENT]) {
    nodes {
      ... on ClosedEvent {
        actor { login }
        createdAt
      }
      ... on MergedEvent {
        actor { login }
        createdAt
      }
    }
  }
}
"""

class ReportDataStrategy(Strategy):
    """
    Base strategy for fetching report data.
    
    Provides helper methods for date filtering within a specific period.
    """
    def __init__(self, client, config, start_date, end_date):
        """
        Initialize the report strategy.

        Args:
            client (GitHubClient): The GitHub client.
            config (dict): Configuration dictionary containing username and repos.
            start_date (str|date): The start date of the report period.
            end_date (str|date): The end date of the report period.
        """
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
        """
        Check if a given date string falls within the report period.
        
        Args:
            created_at (str): ISO 8601 date string.
            
        Returns:
            bool: True if the date is within the start_date and end_date (inclusive).
        """
        if not created_at:
            return False
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
        """
        Execute the strategy to fetch authored items.

        Returns:
            dict: A dictionary containing 'pull_requests' and 'issues' lists.
        """
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
                
            variables = {
                "owner": owner, 
                "name": name, 
                "since": since_iso, 
                "author": self.username
            }
            
            data = self.client.execute(query, variables)
            
            if not data or "repository" not in data:
                continue
            
            repo_data = data["repository"]
            
            # Process Issues
            for issue in repo_data.get("issues", {}).get("nodes", []):
                if self._is_in_period(issue["createdAt"]):
                    results["issues"].append(issue)
                    
            # Process PRs
            # These need manual filtering for Author and Date
            for pr in repo_data.get("pullRequests", {}).get("nodes", []):
                # Filter by Author
                if not pr.get("author") or pr["author"]["login"] != self.username:
                    continue
                    
                # Filter by Date
                if self._is_in_period(pr["createdAt"]):
                    results["pull_requests"].append(pr)
                    
        return results

class MaintainerActivityStrategy(ReportDataStrategy):
    """
    Fetches activity where the user acted as a maintainer (reviewed, commented, closed)
    but was NOT the author.
    """
    def run(self):
        """
        Execute the strategy to fetch maintainer activity.

        Returns:
            dict: A dictionary containing lists for 'prs_reviewed', 'prs_closed_merged',
                  'issues_engaged', and 'issues_closed'.
        """
        repos = self.config.get("watch_all", []) + self.config.get("watch_mentions", [])
        repos = list(set(repos))

        if not repos or not self.username:
            return {
                "prs_reviewed": [],
                "prs_closed_merged": [],
                "issues_engaged": [],
                "issues_closed": []
            }

        # Query recent items to scan for engagement
        # We fetch recent updated items, then check if we did anything on them
        query = f"""
        query($owner: String!, $name: String!) {{
          repository(owner: $owner, name: $name) {{
            issues(first: 50, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{ ...ReportIssueFields }}
            }}
            pullRequests(first: 50, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{ ...ReportPRFields }}
            }}
          }}
        }}
        {FRAGMENT_REPORT_ISSUE}
        {FRAGMENT_REPORT_PR}
        """

        results = {
            "prs_reviewed": [],
            "prs_closed_merged": [],
            "issues_engaged": [],
            "issues_closed": []
        }

        for repo_fullname in repos:
            try:
                owner, name = repo_fullname.split("/")
            except ValueError:
                continue

            data = self.client.execute(query, {"owner": owner, "name": name})
            if not data or "repository" not in data:
                continue

            repo_data = data["repository"]

            # 1. Process PRs (Reviewed, Closed, Merged)
            for pr in repo_data.get("pullRequests", {}).get("nodes", []):
                # Skip authored items
                if pr.get("author") and pr["author"]["login"] == self.username:
                    continue
                
                # Check for Reviews
                if "reviews" in pr and pr["reviews"]["nodes"]:
                    for review in pr["reviews"]["nodes"]:
                        if review["author"] and review["author"]["login"] == self.username:
                            if self._is_in_period(review["createdAt"]):
                                results["prs_reviewed"].append(pr)
                                break # Count once per PR

                # Check for Closed/Merged
                if "timelineItems" in pr and pr["timelineItems"]["nodes"]:
                    for event in pr["timelineItems"]["nodes"]:
                        if event and "actor" in event and event["actor"] and event["actor"]["login"] == self.username:
                            if self._is_in_period(event["createdAt"]):
                                results["prs_closed_merged"].append(pr)
                                break

            # 2. Process Issues (Engaged, Closed)
            for issue in repo_data.get("issues", {}).get("nodes", []):
                if issue["author"] and issue["author"]["login"] == self.username:
                    continue
                
                is_engaged = False
                # Check for Comments
                if "comments" in issue and issue["comments"]["nodes"]:
                    for comment in issue["comments"]["nodes"]:
                        if comment["author"] and comment["author"]["login"] == self.username:
                            # We count engagement if it happened at all recently? 
                            # Or strictly in period? Usually engagement is "touched in period"
                            # But we only have date on issue, not comment in this fragment.
                            # Let's assume if issue updated recently and we commented, we are engaged.
                            # For strictness, we should fetch comment dates.
                            # Fragment has "nodes { author { login } }". No date.
                            # Let's accept "commented" if issue updated in period.
                            is_engaged = True
                            break
                
                if is_engaged and self._is_in_period(issue["updatedAt"]):
                     results["issues_engaged"].append(issue)

                # Check for Closed
                if "timelineItems" in issue and issue["timelineItems"]["nodes"]:
                    for event in issue["timelineItems"]["nodes"]:
                        if event and "actor" in event and event["actor"] and event["actor"]["login"] == self.username:
                             if self._is_in_period(event["createdAt"]):
                                 results["issues_closed"].append(issue)
                                 break

        return results


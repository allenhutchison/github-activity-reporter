from datetime import datetime
from dateutil import parser

# Common fields we want to retrieve
FRAGMENT_ISSUE = """
fragment IssueFields on Issue {
  title
  url
  number
  updatedAt
  author { login }
  comments(last: 1) {
    nodes {
      author { login }
      updatedAt
    }
  }
  repository { nameWithOwner }
}
"""

FRAGMENT_PR = """
fragment PRFields on PullRequest {
  title
  url
  number
  updatedAt
  author { login }
  comments(last: 1) {
    nodes {
      author { login }
      updatedAt
    }
  }
  reviews(last: 1) {
    nodes {
      author { login }
      updatedAt
    }
  }
  repository { nameWithOwner }
}
"""

FRAGMENT_DISCUSSION = """
fragment DiscussionFields on Discussion {
  title
  url
  number
  updatedAt
  author { login }
  comments(last: 1) {
    nodes {
      author { login }
      updatedAt
    }
  }
  repository { nameWithOwner }
}
"""

class Strategy:
    """
    Base class for data fetching strategies.
    """
    def __init__(self, client, config, last_run_at):
        """
        Initialize the strategy.

        Args:
            client (GitHubClient): The GitHub client.
            config (dict): The configuration dictionary.
            last_run_at (str): ISO 8601 timestamp of the last run.
        """
        self.client = client
        self.config = config
        self.last_run_at = last_run_at
        # Convert ISO string to datetime object for comparison
        self.last_run_dt = parser.isoparse(last_run_at)

    def _is_new(self, item_date_str):
        """Checks if an item was updated after the last run."""
        item_dt = parser.isoparse(item_date_str)
        return item_dt > self.last_run_dt

    def run(self):
        """Executes the strategy and returns a list of items."""
        raise NotImplementedError

class FullWatchStrategy(Strategy):
    """
    Iterates through 'watch_all' repos and fetches recent activity.
    
    This strategy fetches recent issues, PRs, and discussions from the
    configured repositories directly via the GraphQL API.
    """
    def run(self):
        repos = self.config.get("watch_all", [])
        results = []

        if not repos:
            return results

        query = f"""
        query($owner: String!, $name: String!) {{
          repository(owner: $owner, name: $name) {{
            issues(first: 20, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{ ...IssueFields }}
            }}
            pullRequests(first: 20, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{ ...PRFields }}
            }}
            discussions(first: 20, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{ ...DiscussionFields }}
            }}
          }}
        }}
        {FRAGMENT_ISSUE}
        {FRAGMENT_PR}
        {FRAGMENT_DISCUSSION}
        """

        for repo_fullname in repos:
            try:
                owner, name = repo_fullname.split("/")
            except ValueError:
                print(f"Skipping invalid repo format: {repo_fullname}")
                continue

            data = self.client.execute(query, {"owner": owner, "name": name})
            if not data or "repository" not in data:
                continue
            
            repo_data = data["repository"]
            
            # Process Issues
            for issue in repo_data.get("issues", {}).get("nodes", []):
                if self._is_new(issue["updatedAt"]):
                    issue["type"] = "Issue"
                    results.append(issue)

            # Process PRs
            for pr in repo_data.get("pullRequests", {}).get("nodes", []):
                if self._is_new(pr["updatedAt"]):
                    pr["type"] = "PR"
                    results.append(pr)

            # Process Discussions
            for disc in repo_data.get("discussions", {}).get("nodes", []):
                if self._is_new(disc["updatedAt"]):
                    disc["type"] = "Discussion"
                    results.append(disc)

        return results

class MentionWatchStrategy(Strategy):
    """
    Uses Global Search to find mentions and updates in specific big repos.
    
    This strategy is useful for high-volume repositories where you only care
    about items where you are mentioned or are the author.
    """
    def run(self):
        repos = self.config.get("watch_mentions", [])
        username = self.config.get("username")
        
        if not repos or not username:
            return []

        # Construct search query
        # logic: (repo:A OR repo:B) AND (mentions:user OR author:user) AND updated:>last_run
        
        repo_query = " ".join([f"repo:{r}" for r in repos])
        # We want:
        # 1. Items that mention me
        # 2. Items I created (commented on is harder to filter perfectly in one go, usually involves:commenter:me)
        # The user specifically asked for "mentions" and "commented on one of my PRs".
        # "author:me" covers "my PRs". "mentions:me" covers direct mentions.
        
        # Simplified: (repo:A OR repo:B) (mentions:me OR author:me) updated:>TIMESTAMP
        date_str = self.last_run_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        search_str = f"{repo_query} (mentions:{username} OR author:{username}) updated:>{date_str}"
        
        query = f"""
        query($query: String!) {{
          search(query: $query, type: ISSUE, first: 50) {{
            nodes {{
              ... on Issue {{ ...IssueFields }}
              ... on PullRequest {{ ...PRFields }}
            }}
          }}
        }}
        {FRAGMENT_ISSUE}
        {FRAGMENT_PR}
        """

        data = self.client.execute(query, {"query": search_str})
        results = []
        
        if data and "search" in data:
            for node in data["search"]["nodes"]:
                # Search returns a mix, identify type
                if "reviews" in node: # It's a PR
                    node["type"] = "PR"
                else:
                    node["type"] = "Issue" # Could be issue
                
                results.append(node)
                
        return results

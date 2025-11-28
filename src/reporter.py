import os
import json
from datetime import date
from src.client import GitHubClient
from src.report_strategies import AuthoredActivityStrategy

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

def collect_data_graphql(token, start_date, end_date, repos):
    """
    Collects GitHub activity data using GraphQL and returns it as structured data.
    """
    try:
        client = GitHubClient()
        
        # Fetch current user login
        user_query = "query { viewer { login } }"
        user_data = client.execute(user_query)
        if not user_data:
             return None, "Failed to fetch user data"
        username = user_data["viewer"]["login"]
        
        # Configure strategy
        config = {
            "username": username,
            "watch_all": repos,
            "watch_mentions": []
        }
        
        strategy = AuthoredActivityStrategy(client, config, start_date, end_date)
        data = strategy.run()
        
        # Initialize data structure
        report_data = {
            "username": username,
            "period": {"start": start_date, "end": end_date},
            "repositories": repos,
            "contributions": {
                "pull_requests": [],
                "issues": [],
                "commits": []
            },
            "maintainer_work": {
                "prs_reviewed": [],
                "prs_closed_merged": [],
                "issues_engaged": [],
                "issues_closed": []
            }
        }
        
        # Process Pull Requests
        for pr in data["pull_requests"]:
            status = "open"
            if pr.get("mergedAt"):
                status = "merged"
            elif pr.get("state") == "CLOSED":
                status = "closed"
                
            commits_list = []
            if "commits" in pr and "nodes" in pr["commits"]:
                for node in pr["commits"]["nodes"]:
                    c = node["commit"]
                    # Check if author exists and matches (GraphQL might return null author for some bot commits etc)
                    if c.get("author") and c["author"].get("user") and c["author"]["user"]["login"] == username:
                        commits_list.append({
                            "sha": c["oid"][:7],
                            "url": c["url"],
                            "message": c["message"].split('\n')[0]
                        })
            
            report_data["contributions"]["pull_requests"].append({
                "number": pr["number"],
                "url": pr["url"],
                "title": pr["title"],
                "status": status,
                "commits": commits_list
            })
            
        # Process Issues
        for issue in data["issues"]:
            status = "closed" if issue["state"] == "CLOSED" else "open"
            report_data["contributions"]["issues"].append({
                "number": issue["number"],
                "url": issue["url"],
                "title": issue["title"],
                "status": status
            })
            
        return report_data, None

    except Exception as e:
        return None, f"GraphQL collection failed: {e}"

def generate_narrative(report_data, gemini_model="gemini-2.5-flash"):
    """
    Uses Google's Gemini API to generate a human-readable narrative.
    """
    if not GENAI_AVAILABLE:
        return None, "Google Genai is not installed. Install it with: pip install google-genai"

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return None, "Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."

    client = genai.Client(api_key=api_key)

    prompt = f"""You are a technical writer who creates engaging narratives about software development work.

Given the following GitHub activity data, create a comprehensive but readable narrative that:
1. Summarizes the key accomplishments and contributions
2. Highlights the most impactful work (merged PRs, critical bug fixes, etc.)
3. Shows collaboration and community engagement
4. Groups related work together thematically
5. Uses a professional but conversational tone
6. Includes specific examples and technical details where relevant
7. Organizes the narrative in a logical flow (major features → bug fixes → maintenance → community work)

Format the output as a well-structured narrative with:
- An executive summary paragraph
- Themed sections with descriptive headers
- Specific examples with PR/issue numbers for reference
- A concluding paragraph about ongoing work and future directions

Make the narrative informative for both technical and non-technical readers.

GitHub Activity Data:
{json.dumps(report_data, indent=2)}

Please create a narrative summary that tells the story of what was accomplished during this period, making connections between related work, and highlighting the impact of the contributions."""

    try:
        response = client.models.generate_content(
            model=gemini_model,
            contents=prompt
        )
        if response and response.text:
            return response.text, None
        else:
            return None, "No narrative text generated"
    except Exception as e:
        return None, f"Failed to generate narrative: {e}"

def format_markdown_report(report_data):
    """
    Formats the report data as markdown.
    """
    output = []

    output.append(f"# GitHub Activity Report for {report_data['username']}")
    output.append(f"**Period:** `{report_data['period']['start']}` to `{report_data['period']['end']}`")
    output.append(f"**Repositories:** {', '.join(report_data['repositories'])}\n")

    # Contributions
    output.append("## 📝 Contributions")
    output.append("_Pull requests, issues, and commits authored by you_\n")

    output.append("### Pull Requests Authored")
    if report_data["contributions"]["pull_requests"]:
        for pr in report_data["contributions"]["pull_requests"]:
            output.append(f"- [#{pr['number']}]({pr['url']}) - {pr['title']} _({pr['status']})_")
            for commit in pr["commits"][:5]:
                output.append(f"  - [`{commit['sha']}`]({commit['url']}) - {commit['message']}")
            if len(pr["commits"]) > 5:
                output.append(f"  - ... and {len(pr['commits']) - 5} more commits")
    else:
        output.append("- No pull requests authored during this period.")

    output.append("\n### Issues Created")
    if report_data["contributions"]["issues"]:
        for issue in report_data["contributions"]["issues"]:
            output.append(f"- [#{issue['number']}]({issue['url']}) - {issue['title']} _({issue['status']})_")
    else:
        output.append("- No issues created during this period.")

    # Maintainer Work
    output.append("\n## 🔧 Maintainer Work")
    output.append("_Code reviews, issue triage, and community engagement_\n")

    output.append("### Pull Requests Reviewed")
    if report_data["maintainer_work"]["prs_reviewed"]:
        for pr in report_data["maintainer_work"]["prs_reviewed"]:
            output.append(f"- [#{pr['number']}]({pr['url']}) - {pr['title']} _({pr['state']})_")
    else:
        output.append("- No pull requests reviewed during this period.")

    output.append("\n### Issue Engagement")
    if report_data["maintainer_work"]["issues_engaged"]:
        for issue in report_data["maintainer_work"]["issues_engaged"]:
            interactions = ", ".join(issue['interactions'])
            output.append(f"- [#{issue['number']}]({issue['url']}) - {issue['title']} _({interactions}, {issue['state']})_")
    else:
        output.append("- No issue engagement during this period.")

    output.append("\n---")
    output.append(f"_Report generated on {date.today()}_")

    return "\n".join(output)

def generate_report(token, start_date, end_date, repos, use_narrative=False, gemini_model="gemini-2.5-flash"):
    """
    Generates a report of GitHub activity for a user within a specified date range and repositories.
    Can optionally use Google's ADK to generate a human-readable narrative.
    """
    # Collect GitHub data
    report_data, error = collect_data_graphql(token, start_date, end_date, repos)
    if error:
        print(f"Error: {error}")
        return

    # Generate output based on mode
    if use_narrative:
        # First print the structured report
        print("## 📊 Structured Report\n")
        print(format_markdown_report(report_data))

        # Then generate and print the narrative
        print("\n\n## 📖 Narrative Summary\n")
        narrative, error = generate_narrative(report_data, gemini_model)
        if error:
            print(f"Error generating narrative: {error}")
            print("Falling back to structured report only.")
        elif narrative:
            print(narrative)
        else:
            print("Could not generate narrative. Please check your Gemini API configuration.")
    else:
        # Just print the markdown report
        print(format_markdown_report(report_data))

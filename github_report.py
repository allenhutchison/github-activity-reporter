#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pygithub",
#     "google-genai",
# ]
# ///

import argparse
import os
import sys
import json
from datetime import datetime, date
from github import Github
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError as e:
    GENAI_AVAILABLE = False
    GENAI_IMPORT_ERROR = str(e)

def run_search_for_repos(g, base_query, repos):
    """
    Run a search query for each repo individually and combine results.
    This handles mixed public/private repos better than a single combined query.
    """
    all_results = []
    for repo in repos:
        if "/" in repo:
            repo_qualifier = f"repo:{repo}"
        else:
            repo_qualifier = f"org:{repo}"

        full_query = f"{base_query} {repo_qualifier}"
        try:
            results = g.search_issues(query=full_query, sort="created", order="desc")
            for item in results:
                all_results.append(item)
        except Exception as e:
            # Skip repos we can't access or that have errors
            pass

    return all_results

def run_commit_search_for_repos(g, base_query, repos):
    """
    Run a commit search query for each repo individually and combine results.
    """
    all_results = []
    for repo in repos:
        if "/" in repo:
            repo_qualifier = f"repo:{repo}"
        else:
            repo_qualifier = f"org:{repo}"

        full_query = f"{base_query} {repo_qualifier}"
        try:
            results = g.search_commits(query=full_query, sort="committer-date", order="desc")
            for item in results:
                all_results.append(item)
        except Exception as e:
            # Skip repos we can't access or that have errors
            pass

    return all_results

def collect_github_data(token, start_date, end_date, repos):
    """
    Collects GitHub activity data and returns it as structured data.
    """
    try:
        g = Github(token)
        user = g.get_user()
        username = user.login
    except Exception as e:
        return None, f"Failed to authenticate with GitHub: {e}"

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

    date_qualifier = f"created:{start_date}..{end_date}"
    updated_date_qualifier = f"updated:{start_date}..{end_date}"
    closed_date_qualifier = f"closed:{start_date}..{end_date}"

    # Collect Pull Requests Authored
    prs = run_search_for_repos(g, f"is:pr author:{username} {date_qualifier}", repos)
    pr_commit_shas = set()

    if prs:
        seen = set()
        for pr in sorted(prs, key=lambda x: x.created_at, reverse=True):
            if pr.number not in seen:
                seen.add(pr.number)
                status = "merged" if pr.pull_request.merged_at else ("closed" if pr.state == "closed" else "open")
                pr_data = {
                    "number": pr.number,
                    "url": pr.html_url,
                    "title": pr.title,
                    "status": status,
                    "commits": []
                }

                # Try to get commits for this PR
                try:
                    repo_name = pr.repository.full_name
                    repo_obj = g.get_repo(repo_name)
                    pr_obj = repo_obj.get_pull(pr.number)
                    commits = pr_obj.get_commits()

                    for commit in commits:
                        pr_commit_shas.add(commit.sha)
                        if commit.author and commit.author.login == username:
                            message_first_line = commit.commit.message.split('\n')[0]
                            pr_data["commits"].append({
                                "sha": commit.sha[:7],
                                "url": commit.html_url,
                                "message": message_first_line
                            })
                except:
                    pass

                report_data["contributions"]["pull_requests"].append(pr_data)

    # Collect Issues Created
    issues = run_search_for_repos(g, f"is:issue author:{username} {date_qualifier}", repos)
    if issues:
        seen = set()
        for issue in sorted(issues, key=lambda x: x.created_at, reverse=True):
            if issue.number not in seen:
                seen.add(issue.number)
                status = "closed" if issue.state == "closed" else "open"
                report_data["contributions"]["issues"].append({
                    "number": issue.number,
                    "url": issue.html_url,
                    "title": issue.title,
                    "status": status
                })

    # Collect Work in Progress (Commits not in PRs)
    commits = run_commit_search_for_repos(g, f"author:{username} committer-date:{start_date}..{end_date}", repos)

    orphan_commits = []
    for commit in commits:
        if commit.sha not in pr_commit_shas:
            orphan_commits.append(commit)

    if orphan_commits:
        repo_commits = {}
        for commit in orphan_commits:
            repo_name = commit.repository.full_name
            if repo_name not in repo_commits:
                repo_commits[repo_name] = []
            message_first_line = commit.commit.message.split('\n')[0]
            repo_commits[repo_name].append({
                "sha": commit.sha[:7],
                "url": commit.html_url,
                "message": message_first_line,
                "repo": repo_name
            })

        for repo_name, commit_list in repo_commits.items():
            report_data["contributions"]["commits"].extend(commit_list[:10])

    # Collect Pull Request Reviews
    pr_reviewed = set()

    reviewed_prs = run_search_for_repos(g, f"is:pr commenter:{username} {updated_date_qualifier}", repos)
    for pr in reviewed_prs:
        if pr.pull_request and pr.user.login != username:
            pr_reviewed.add((pr.number, pr.html_url, pr.title, pr.state))

    reviewed_prs = run_search_for_repos(g, f"is:pr reviewed-by:{username} {updated_date_qualifier}", repos)
    for pr in reviewed_prs:
        if pr.user.login != username:
            pr_reviewed.add((pr.number, pr.html_url, pr.title, pr.state))

    for number, url, title, state in pr_reviewed:
        report_data["maintainer_work"]["prs_reviewed"].append({
            "number": number,
            "url": url,
            "title": title,
            "state": state
        })

    # Collect Pull Requests Closed/Merged
    prs_closed = {}

    closed_prs = run_search_for_repos(g, f"is:pr is:closed author:{username} {closed_date_qualifier}", repos)
    for pr in closed_prs:
        if pr.pull_request.merged_at:
            prs_closed[pr.number] = (pr.html_url, pr.title, "merged (author)")
        else:
            prs_closed[pr.number] = (pr.html_url, pr.title, "closed (author)")

    reviewed_closed = run_search_for_repos(g, f"is:pr is:closed reviewed-by:{username} {closed_date_qualifier}", repos)
    for pr in reviewed_closed:
        if pr.user.login != username and pr.number not in prs_closed:
            status = "merged (reviewed)" if pr.pull_request.merged_at else "closed (reviewed)"
            prs_closed[pr.number] = (pr.html_url, pr.title, status)

    for number in prs_closed.keys():
        url, title, status = prs_closed[number]
        report_data["maintainer_work"]["prs_closed_merged"].append({
            "number": number,
            "url": url,
            "title": title,
            "status": status
        })

    # Collect Issue Engagement
    issues_engaged = {}

    commented_issues = run_search_for_repos(g, f"is:issue commenter:{username} {updated_date_qualifier}", repos)
    for issue in commented_issues:
        if issue.user.login != username:
            if issue.number not in issues_engaged:
                issues_engaged[issue.number] = {
                    'url': issue.html_url,
                    'title': issue.title,
                    'state': issue.state,
                    'interactions': set()
                }
            issues_engaged[issue.number]['interactions'].add("commented")

    mentioned_issues = run_search_for_repos(g, f"is:issue mentions:{username} {updated_date_qualifier}", repos)
    for issue in mentioned_issues:
        if issue.user.login != username:
            if issue.number not in issues_engaged:
                issues_engaged[issue.number] = {
                    'url': issue.html_url,
                    'title': issue.title,
                    'state': issue.state,
                    'interactions': set()
                }
            issues_engaged[issue.number]['interactions'].add("mentioned")

    assigned_issues = run_search_for_repos(g, f"is:issue assignee:{username} {updated_date_qualifier}", repos)
    for issue in assigned_issues:
        if issue.user.login != username:
            if issue.number not in issues_engaged:
                issues_engaged[issue.number] = {
                    'url': issue.html_url,
                    'title': issue.title,
                    'state': issue.state,
                    'interactions': set()
                }
            issues_engaged[issue.number]['interactions'].add("assigned")

    for number, issue_data in issues_engaged.items():
        report_data["maintainer_work"]["issues_engaged"].append({
            "number": number,
            "url": issue_data['url'],
            "title": issue_data['title'],
            "state": issue_data['state'],
            "interactions": list(issue_data['interactions'])
        })

    # Collect Issues Closed
    issues_closed = {}

    closed_authored = run_search_for_repos(g, f"is:issue is:closed author:{username} {closed_date_qualifier}", repos)
    for issue in closed_authored:
        issues_closed[issue.number] = (issue.html_url, issue.title, "authored & closed")

    closed_commented = run_search_for_repos(g, f"is:issue is:closed commenter:{username} {closed_date_qualifier}", repos)
    for issue in closed_commented:
        if issue.user.login != username and issue.number not in issues_closed:
            try:
                comments = list(issue.get_comments())
                if comments:
                    recent_comments = comments[-5:] if len(comments) > 5 else comments
                    for comment in recent_comments:
                        if comment.user.login == username:
                            comment_date = comment.created_at.strftime('%Y-%m-%d')
                            if start_date <= comment_date <= end_date:
                                comment_lower = comment.body.lower()
                                if any(word in comment_lower for word in ['duplicate', 'closing', 'fixed', 'resolved', 'close']):
                                    issues_closed[issue.number] = (issue.html_url, issue.title, "closed as duplicate/resolved")
                                else:
                                    issues_closed[issue.number] = (issue.html_url, issue.title, "closed after commenting")
                                break
            except:
                if issue.number not in issues_closed:
                    issues_closed[issue.number] = (issue.html_url, issue.title, "involved in closure")

    closed_assigned = run_search_for_repos(g, f"is:issue is:closed assignee:{username} {closed_date_qualifier}", repos)
    for issue in closed_assigned:
        if issue.user.login != username and issue.number not in issues_closed:
            issues_closed[issue.number] = (issue.html_url, issue.title, "assigned & closed")

    for number in issues_closed.keys():
        url, title, reason = issues_closed[number]
        report_data["maintainer_work"]["issues_closed"].append({
            "number": number,
            "url": url,
            "title": title,
            "reason": reason
        })

    return report_data, None

def generate_narrative(report_data, gemini_model="gemini-2.5-flash"):
    """
    Uses Google's Gemini API to generate a human-readable narrative from the GitHub activity data.
    """
    if not GENAI_AVAILABLE:
        import_error = globals().get('GENAI_IMPORT_ERROR', 'Unknown import error')
        return None, f"Google Genai is not installed. Install it with: pip install google-genai (Error: {import_error})"

    # Check for Gemini/Google API key
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return None, "Gemini API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable."

    # Create the client with API key
    client = genai.Client(api_key=api_key)

    # Prepare the prompt
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
        # Generate the narrative
        response = client.models.generate_content(
            model=gemini_model,
            contents=prompt
        )

        # Extract the text from the response
        if response and response.text:
            return response.text, None
        else:
            return None, "No narrative text generated"

    except Exception as e:
        return None, f"Failed to generate narrative: {e}"

def format_markdown_report(report_data):
    """
    Formats the report data as markdown (original format).
    """
    output = []

    output.append(f"# GitHub Activity Report for {report_data['username']}")
    output.append(f"**Period:** `{report_data['period']['start']}` to `{report_data['period']['end']}`")
    output.append(f"**Repositories:** {', '.join(report_data['repositories'])}\n")

    # Contributions Section
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

    output.append("\n### Work in Progress")
    output.append("_Commits not yet part of a pull request_")
    if report_data["contributions"]["commits"]:
        current_repo = None
        for commit in report_data["contributions"]["commits"]:
            if commit.get("repo") != current_repo:
                current_repo = commit.get("repo", "unknown")
                output.append(f"\n#### `{current_repo}`")
            output.append(f"- [`{commit['sha']}`]({commit['url']}) - {commit['message']}")
    else:
        output.append("- All recent commits are part of pull requests")

    # Maintainer Work Section
    output.append("\n## 🔧 Maintainer Work")
    output.append("_Code reviews, issue triage, and community engagement_\n")

    output.append("### Pull Requests Reviewed")
    if report_data["maintainer_work"]["prs_reviewed"]:
        for pr in report_data["maintainer_work"]["prs_reviewed"]:
            output.append(f"- [#{pr['number']}]({pr['url']}) - {pr['title']} _({pr['state']})_")
    else:
        output.append("- No pull requests reviewed during this period.")

    output.append("\n### Pull Requests Closed/Merged")
    if report_data["maintainer_work"]["prs_closed_merged"]:
        for pr in report_data["maintainer_work"]["prs_closed_merged"]:
            output.append(f"- [#{pr['number']}]({pr['url']}) - {pr['title']} _({pr['status']})_")
    else:
        output.append("- No pull requests closed/merged during this period.")

    output.append("\n### Issue Engagement")
    if report_data["maintainer_work"]["issues_engaged"]:
        for issue in report_data["maintainer_work"]["issues_engaged"]:
            interactions = ", ".join(issue['interactions'])
            output.append(f"- [#{issue['number']}]({issue['url']}) - {issue['title']} _({interactions}, {issue['state']})_")
    else:
        output.append("- No issue engagement during this period.")

    output.append("\n### Issues Closed")
    if report_data["maintainer_work"]["issues_closed"]:
        for issue in report_data["maintainer_work"]["issues_closed"]:
            output.append(f"- [#{issue['number']}]({issue['url']}) - {issue['title']} _({issue['reason']})_")
    else:
        output.append("- No issues closed during this period.")

    output.append("\n---")
    output.append(f"_Report generated on {date.today()}_")

    return "\n".join(output)

def generate_report(token, start_date, end_date, repos, use_narrative=False, gemini_model="gemini-2.5-flash"):
    """
    Generates a report of GitHub activity for a user within a specified date range and repositories.
    Can optionally use Google's ADK to generate a human-readable narrative.
    """
    # Collect GitHub data
    report_data, error = collect_github_data(token, start_date, end_date, repos)
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


def main():
    parser = argparse.ArgumentParser(description="Generate a GitHub activity report.")
    parser.add_argument("--token", help="GitHub Personal Access Token (or set GITHUB_TOKEN env var).")
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD format (defaults to today).")
    parser.add_argument("--end-date", help="End date in YYYY-MM-DD format (defaults to today).")
    parser.add_argument("--repos", nargs='+', required=True,
                        help="A list of repositories (user/repo) or organizations (org) to include in the report.")
    parser.add_argument("--narrative", action="store_true",
                        help="Generate a human-readable narrative using Google's Gemini API (requires google-genai package).")
    parser.add_argument("--gemini-model", default="gemini-2.5-flash",
                        help="Gemini model to use for narrative generation (default: gemini-2.5-flash).")

    args = parser.parse_args()

    # Get token from args or environment variable
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token required. Pass --token or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    # Default dates to today if not provided
    today = date.today().strftime('%Y-%m-%d')
    start_date = args.start_date or today
    end_date = args.end_date or today

    generate_report(token, start_date, end_date, args.repos,
                   use_narrative=args.narrative,
                   gemini_model=args.gemini_model)

if __name__ == "__main__":
    main()
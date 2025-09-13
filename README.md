# GitHub Activity Reporter

Generate comprehensive GitHub activity reports with AI-powered narratives. Perfect for standup meetings, performance reviews, or tracking your open source contributions.

## Features

- **📊 Comprehensive Activity Tracking**
  - Pull requests (authored, reviewed, merged)
  - Issues (created, engaged, closed)
  - Commits (including work-in-progress)
  - Maintainer activities

- **🤖 AI-Powered Narratives** (Optional)
  - Generate human-readable summaries using Google's Gemini API
  - Intelligently groups related work
  - Professional tone suitable for reports and reviews

- **🔍 Flexible Reporting**
  - Track activity across multiple repositories and organizations
  - Custom date ranges (daily, weekly, monthly, etc.)
  - Works with both public and private repositories

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/github-activity-reporter.git
cd github-activity-reporter

# Install dependencies
pip install -r requirements.txt

# Or use pipx for isolated installation
pipx install pygithub google-genai
```

### Basic Usage

```bash
# Generate today's activity report
python github_report.py --repos owner/repo

# Specify date range
python github_report.py \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --repos owner/repo org

# Generate AI narrative (requires Gemini API key)
python github_report.py \
  --narrative \
  --repos owner/repo
```

## Setup

### 1. GitHub Token

Create a GitHub Personal Access Token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token" (classic)
3. Select scopes: `repo`, `read:org`, `read:user`
4. Save the token

Set the token as an environment variable:
```bash
export GITHUB_TOKEN="your_token_here"
```

### 2. Gemini API Key (Optional, for AI narratives)

Get a Gemini API key:
1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Set it as an environment variable:

```bash
export GEMINI_API_KEY="your_api_key_here"
```

## Usage Examples

### Daily Standup Report
```bash
# Today's activity across multiple repos
python github_report.py \
  --repos myorg/frontend myorg/backend myorg/docs
```

### Weekly Team Report
```bash
# Last week's activity with AI narrative
python github_report.py \
  --start-date 2024-01-15 \
  --end-date 2024-01-21 \
  --narrative \
  --repos myteam
```

### Monthly Contribution Summary
```bash
# Track open source contributions
python github_report.py \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --narrative \
  --repos facebook/react vuejs/vue microsoft/vscode
```

### Performance Review Documentation
```bash
# Quarterly report with detailed commits
python github_report.py \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --narrative \
  --gemini-model gemini-2.5-pro \
  --repos mycompany > Q1_performance_review.md
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--token` | GitHub Personal Access Token | `$GITHUB_TOKEN` |
| `--start-date` | Start date (YYYY-MM-DD) | Today |
| `--end-date` | End date (YYYY-MM-DD) | Today |
| `--repos` | Space-separated list of repos/orgs | Required |
| `--narrative` | Generate AI narrative summary | False |
| `--gemini-model` | Gemini model for narratives | gemini-2.5-flash |

## Output Format

### Standard Report
- Structured markdown with sections for:
  - Pull Requests (with commit details)
  - Issues (created and status)
  - Work in Progress (orphan commits)
  - Maintainer activities (reviews, triage)

### With AI Narrative
- Includes both structured report and narrative summary
- Executive summary
- Thematically grouped accomplishments
- Impact analysis and future directions

## Tips

1. **For Team Leads**: Use the narrative mode to quickly generate team update emails
2. **For Contributors**: Track contributions across multiple open source projects
3. **For Performance Reviews**: Generate comprehensive activity logs with context
4. **For Daily Standups**: Run with today's date for a quick activity summary

## Privacy & Security

- The script only accesses repositories you have permission to view
- GitHub token is never stored (only used at runtime)
- Gemini API processes data according to Google's privacy policy
- All data processing happens locally except for optional AI narrative generation

## Troubleshooting

### "Repository not found" errors
- Ensure your GitHub token has appropriate permissions
- Check repository names are correct (case-sensitive)

### No activity shown
- Verify date range is correct
- Check that your GitHub username matches the token owner
- Ensure repos parameter includes correct organizations/repositories

### Gemini API errors
- Verify API key is set correctly
- Check API quotas and limits
- Try using a different model (e.g., `--gemini-model gemini-2.5-flash`)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Author

Originally created for personal use, now shared with the community.

## Acknowledgments

- Built with [PyGithub](https://github.com/PyGithub/PyGithub)
- AI narratives powered by [Google Gemini](https://ai.google.dev/)

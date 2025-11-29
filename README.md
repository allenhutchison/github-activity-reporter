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

- **🔐 Multiple Authentication Methods**
  - OAuth device flow (recommended for easy setup)
  - Personal access tokens
  - Environment variables
  - Secure local token storage

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
# First time: Authenticate with OAuth
python github_report.py --oauth-login

# Generate today's activity report
python github_report.py --use-oauth --repos owner/repo

# Specify date range
python github_report.py \
  --use-oauth \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --repos owner/repo org

# Generate AI narrative (requires Gemini API key)
python github_report.py \
  --use-oauth \
  --narrative \
  --repos owner/repo

# Using environment variable instead of OAuth
export GITHUB_TOKEN="your_token_here"
python github_report.py --repos owner/repo
```

## Setup

### Authentication Options

You can authenticate with GitHub in two ways:

#### Option 1: OAuth (Recommended)

OAuth provides a better user experience with automatic token management.

**Step 1: Register a GitHub OAuth App (one-time setup)**

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **"OAuth Apps"** → **"New OAuth App"**
3. Fill in the registration form:
   - **Application name**: `GitHub Activity Reporter` (or your choice)
   - **Homepage URL**: `https://github.com/yourusername/github-activity-reporter` (or any URL)
   - **Authorization callback URL**: `http://localhost` (required but not used for device flow)
4. Click **"Register application"**
5. Copy the **Client ID** from the app settings page

**Step 2: Set your Client ID**

Choose one of these methods:

```bash
# Method A: Environment variable (recommended)
export GITHUB_OAUTH_CLIENT_ID="your_client_id_here"

# Method B: Command line flag
python github_report.py --oauth-client-id your_client_id_here --oauth-login

# Method C: Edit github_oauth.py
# Set DEFAULT_CLIENT_ID = "your_client_id_here" in the file
```

**Step 3: Authenticate**

```bash
# First time: authenticate with OAuth
python github_report.py --oauth-login

# Then run reports normally (uses saved token)
python github_report.py --use-oauth --repos owner/repo
```

The OAuth flow will:
1. Display a verification code
2. Open your browser to GitHub
3. Prompt you to enter the code
4. Save the token locally for future use

To logout and remove saved token:
```bash
python github_report.py --oauth-logout
```

#### Option 2: Personal Access Token (PAT)

Create a GitHub Personal Access Token:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token" (classic)
3. Select scopes: `repo`, `read:org`, `read:user`
4. Save the token

**Then choose one of these methods to provide the token:**

**A. Using a `.env` file (recommended for local development):**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your token
# GITHUB_TOKEN=ghp_your_token_here

# Run the script (automatically loads .env)
python github_report.py --repos owner/repo
```

**B. Environment variable:**
```bash
export GITHUB_TOKEN="your_token_here"
python github_report.py --repos owner/repo
```

**C. Command line flag:**
```bash
python github_report.py --token your_token_here --repos owner/repo
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
# Using OAuth (recommended)
python github_report.py \
  --use-oauth \
  --repos myorg/frontend myorg/backend myorg/docs

# Or with environment variable
python github_report.py \
  --repos myorg/frontend myorg/backend myorg/docs
```

### Weekly Team Report
```bash
# Last week's activity with AI narrative
python github_report.py \
  --use-oauth \
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

### Authentication Options

| Option | Description | Default |
|--------|-------------|---------|
| `--token` | GitHub Personal Access Token | `$GITHUB_TOKEN` |
| `--use-oauth` | Use OAuth authentication | False |
| `--oauth-login` | Authenticate with OAuth and save token | - |
| `--oauth-logout` | Remove saved OAuth token | - |
| `--oauth-client-id` | Custom OAuth app client ID | Built-in |

### Report Options

| Option | Description | Default |
|--------|-------------|---------|
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

## Authentication Priority

The tool uses the following priority order for authentication:

1. **`--token` flag** - Explicit token passed on command line (highest priority)
2. **Saved OAuth token** - Used when `--use-oauth` is specified or no other token available
3. **`GITHUB_TOKEN` environment variable** - Fallback option

This allows you to mix authentication methods as needed. For example, you can have a saved OAuth token but override it with `--token` for specific runs.

## Privacy & Security

- The script only accesses repositories you have permission to view
- OAuth tokens are stored locally in `~/.config/github-activity-reporter/` with 600 permissions (owner read/write only)
- Personal access tokens are never stored (only used at runtime)
- OAuth tokens can be revoked at any time using `--oauth-logout` or via GitHub settings
- `.env` files containing secrets are excluded from git via `.gitignore`
- Gemini API processes data according to Google's privacy policy
- All data processing happens locally except for optional AI narrative generation

**Important:** Never commit your `.env` file or tokens to version control. The `.gitignore` file is configured to prevent this, but always double-check before pushing.

## Troubleshooting

### OAuth Issues

**"GitHub OAuth app client ID is required"**
- You need to register a GitHub OAuth App first (see Setup → Option 1)
- Set the client ID using `GITHUB_OAUTH_CLIENT_ID` environment variable
- Or pass it via `--oauth-client-id` flag

**"404 Client Error: Not Found" during OAuth**
- This usually means the OAuth client ID is invalid or not set
- Verify you've registered an OAuth app on GitHub
- Double-check the client ID is correct

**"requests library is required for OAuth"**
- Install requests: `pip install requests`
- Or install all dependencies: `pip install -r requirements.txt`

**OAuth authentication fails**
- Try re-authenticating: `python github_report.py --oauth-login`
- Check your internet connection
- Ensure you completed the authorization in the browser

**"No saved token found"**
- Run `python github_report.py --oauth-login` to authenticate first
- Or use a different auth method (PAT with `--token` or `GITHUB_TOKEN` env var)

### "Repository not found" errors
- Ensure your GitHub token has appropriate permissions
- Check repository names are correct (case-sensitive)
- If using OAuth, verify your token has the required scopes (repo, read:org, read:user)

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

# GitHub Activity Reporter

## Project Overview

`github-activity-reporter` is a CLI tool designed to generate comprehensive activity reports for GitHub users. It tracks pull requests, issues, commits, and maintainer activities across specified repositories. A key feature is its integration with Google's Gemini API to generate AI-powered narrative summaries of the tracked activity, making it useful for standups, performance reviews, and status updates.

**Key Technologies:**
- **Language:** Python 3.12+
- **GitHub API:** `PyGithub`
- **AI/LLM:** `google-genai` (Gemini API)
- **CLI:** `argparse`
- **Configuration:** `pyyaml`
- **Package Management:** `uv` (inferred from `uv.lock`) / standard `pip`

## Architecture

- **Entry Point:** `cli.py` handles command-line arguments and dispatches commands (`report` or `inbox`).
- **Configuration:** `config.yaml` stores watched repositories and user preferences.
- **Core Logic:**
    - `src/reporter.py`: Fetches data from GitHub, formats Markdown reports, and interfaces with the Gemini API for narratives.
    - `src/inbox.py`: Handles notification checking (inferred).
    - `src/client.py`: Likely contains shared client initialization logic.
- **Data Flow:**
    1.  User runs `cli.py report`.
    2.  Configuration is loaded from `config.yaml`.
    3.  `src/reporter.py` authenticates with GitHub using `GITHUB_TOKEN`.
    4.  Data is fetched (PRs, issues, commits) via `PyGithub`.
    5.  (Optional) Data is sent to Gemini API via `google-genai` for narrative generation.
    6.  Final report (Markdown + Narrative) is output to the terminal.

## Building and Running

### Prerequisites

- Python 3.12+
- GitHub Personal Access Token (with `repo`, `read:org`, `read:user` scopes)
- (Optional) Google Gemini API Key

### Installation

The project uses `uv` for dependency management, but can also be installed via `pip`.

```bash
# Using uv
uv sync

# Using pip
pip install -r requirements.txt # (if available, otherwise install from pyproject.toml)
pip install .
```

### Configuration

1.  **Environment Variables:**
    ```bash
    export GITHUB_TOKEN="your_github_token"
    export GEMINI_API_KEY="your_gemini_api_key" # Optional
    ```

2.  **`config.yaml`:**
    Edit `config.yaml` to define the repositories you want to watch.
    ```yaml
    watch_all:
      - "owner/repo1"
    watch_mentions:
      - "owner/repo2"
    ```

### Usage Commands

**Generate a Report:**
```bash
# Basic report for the last day
python cli.py report

# Report for specific days with AI narrative
python cli.py report --days 7 --narrative

# Report for specific repositories
python cli.py report --repos owner/repo1 owner/repo2
```

**Check Inbox:**
```bash
python cli.py inbox
```

## Development Conventions

- **Code Structure:** Source code resides in `src/`. The entry point `cli.py` is in the root.
- **Formatting:** Follow standard Python PEP 8 guidelines.
- **Type Hints:** Use Python type hinting where possible.
- **Dependencies:** Managed via `pyproject.toml`.
- **Error Handling:** Gracefully handle API errors (GitHub or Gemini) without crashing the entire application.

#!/usr/bin/env python3
"""
GitHub OAuth Device Flow implementation for CLI applications.

This module handles OAuth authentication using GitHub's device flow,
which is designed for applications that don't have a web browser or
callback URL capability.
"""

import json
import os
import time
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# OAuth app client ID
# Users need to register their own GitHub OAuth app and provide the client ID
# Can be set via:
# 1. Environment variable: GITHUB_OAUTH_CLIENT_ID
# 2. Command line: --oauth-client-id
# 3. Directly in this file (not recommended for shared repos)
DEFAULT_CLIENT_ID = "Ov23liHjQnMws6ypFiTh"  # Set your client ID here or use GITHUB_OAUTH_CLIENT_ID env var

# GitHub OAuth endpoints
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
REVOKE_TOKEN_URL = "https://github.com/settings/tokens"

# Token storage location
CONFIG_DIR = Path.home() / ".config" / "github-activity-reporter"
TOKEN_FILE = CONFIG_DIR / "oauth_token.json"


class GitHubOAuthError(Exception):
    """Base exception for GitHub OAuth errors."""
    pass


class OAuthDeviceFlow:
    """
    Implements GitHub's OAuth device flow for CLI authentication.

    The device flow is ideal for CLI applications:
    1. App requests a device code
    2. User visits verification URL and enters code
    3. App polls GitHub until user completes authorization
    4. App receives access token
    """

    def __init__(self, client_id: Optional[str] = None, scopes: Optional[list] = None):
        """
        Initialize OAuth device flow.

        Args:
            client_id: GitHub OAuth app client ID (uses default if not provided)
            scopes: List of OAuth scopes (defaults to repo, read:org, read:user)
        """
        if not REQUESTS_AVAILABLE:
            raise GitHubOAuthError(
                "requests library is required for OAuth. Install with: pip install requests"
            )

        # Try to get client ID from multiple sources
        self.client_id = (
            client_id or
            os.environ.get('GITHUB_OAUTH_CLIENT_ID') or
            DEFAULT_CLIENT_ID
        )

        # Validate client ID is set
        if not self.client_id:
            raise GitHubOAuthError(
                "GitHub OAuth app client ID is required.\n\n"
                "To set up OAuth:\n"
                "1. Register a GitHub OAuth App:\n"
                "   - Go to: https://github.com/settings/developers\n"
                "   - Click 'OAuth Apps' → 'New OAuth App'\n"
                "   - Fill in the form:\n"
                "     * Application name: GitHub Activity Reporter\n"
                "     * Homepage URL: https://github.com/yourusername/github-activity-reporter\n"
                "     * Authorization callback URL: http://localhost\n"
                "   - Click 'Register application'\n"
                "   - Copy the 'Client ID'\n\n"
                "2. Provide the Client ID using one of these methods:\n"
                "   - Environment variable: export GITHUB_OAUTH_CLIENT_ID='your_client_id'\n"
                "   - Command line flag: --oauth-client-id your_client_id\n"
                "   - Edit github_oauth.py and set DEFAULT_CLIENT_ID\n\n"
                "For more information, see the README."
            )

        self.scopes = scopes or ["repo", "read:org", "read:user"]

    def start_device_flow(self) -> Dict[str, Any]:
        """
        Initiate the device flow by requesting a device code.

        Returns:
            dict: Device flow data including device_code, user_code, and verification_uri
        """
        data = {
            "client_id": self.client_id,
            "scope": " ".join(self.scopes)
        }

        headers = {
            "Accept": "application/json"
        }

        try:
            response = requests.post(DEVICE_CODE_URL, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise GitHubOAuthError(f"Failed to start device flow: {e}")

    def poll_for_token(self, device_code: str, interval: int = 5, expires_in: int = 900) -> str:
        """
        Poll GitHub for access token after user authorization.

        Args:
            device_code: Device code from start_device_flow
            interval: Polling interval in seconds
            expires_in: Expiration time in seconds

        Returns:
            str: Access token
        """
        data = {
            "client_id": self.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }

        headers = {
            "Accept": "application/json"
        }

        start_time = time.time()

        while True:
            if time.time() - start_time > expires_in:
                raise GitHubOAuthError("Device flow expired. Please try again.")

            try:
                response = requests.post(ACCESS_TOKEN_URL, json=data, headers=headers)
                response.raise_for_status()
                result = response.json()

                if "access_token" in result:
                    return result["access_token"]
                elif result.get("error") == "authorization_pending":
                    # Still waiting for user to authorize
                    time.sleep(interval)
                    continue
                elif result.get("error") == "slow_down":
                    # Rate limited, increase interval
                    interval += 5
                    time.sleep(interval)
                    continue
                else:
                    error_msg = result.get("error_description", result.get("error", "Unknown error"))
                    raise GitHubOAuthError(f"Authorization failed: {error_msg}")

            except requests.RequestException as e:
                raise GitHubOAuthError(f"Failed to poll for token: {e}")

    def authenticate(self, open_browser: bool = True) -> str:
        """
        Complete OAuth device flow authentication.

        Args:
            open_browser: Whether to automatically open browser to verification URL

        Returns:
            str: Access token
        """
        print("🔐 Starting GitHub OAuth authentication...\n")

        # Step 1: Request device code
        device_data = self.start_device_flow()

        user_code = device_data["user_code"]
        verification_uri = device_data["verification_uri"]
        device_code = device_data["device_code"]
        interval = device_data.get("interval", 5)
        expires_in = device_data.get("expires_in", 900)

        # Step 2: Display user instructions
        print(f"📋 Please visit: {verification_uri}")
        print(f"🔑 Enter code: {user_code}\n")

        if open_browser:
            try:
                webbrowser.open(verification_uri)
                print("✨ Opening browser automatically...\n")
            except Exception:
                print("⚠️  Could not open browser automatically. Please visit the URL manually.\n")

        print("⏳ Waiting for authorization...")
        print("   (This will complete automatically once you authorize in the browser)\n")

        # Step 3: Poll for token
        try:
            access_token = self.poll_for_token(device_code, interval, expires_in)
            print("✅ Successfully authenticated!\n")
            return access_token
        except GitHubOAuthError as e:
            print(f"❌ Authentication failed: {e}\n")
            raise


def save_token(token: str) -> None:
    """
    Save OAuth token to local config file.

    Args:
        token: GitHub OAuth access token
    """
    # Create config directory if it doesn't exist
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    token_data = {
        "access_token": token,
        "created_at": time.time()
    }

    # Write token file with restricted permissions
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))

    # Set restrictive permissions (owner read/write only)
    if os.name != 'nt':  # Not Windows
        os.chmod(TOKEN_FILE, 0o600)

    print(f"💾 Token saved to: {TOKEN_FILE}")


def load_token() -> Optional[str]:
    """
    Load OAuth token from local config file.

    Returns:
        str: Access token if found, None otherwise
    """
    if not TOKEN_FILE.exists():
        return None

    try:
        token_data = json.loads(TOKEN_FILE.read_text())
        return token_data.get("access_token")
    except (json.JSONDecodeError, IOError):
        return None


def clear_token() -> None:
    """
    Remove saved OAuth token.
    """
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print(f"🗑️  Token removed from: {TOKEN_FILE}")
        print("\nTo revoke the token on GitHub, visit:")
        print(REVOKE_TOKEN_URL)
    else:
        print("ℹ️  No saved token found.")


def get_or_create_token(client_id: Optional[str] = None,
                        scopes: Optional[list] = None,
                        force_new: bool = False) -> str:
    """
    Get existing token or create new one via OAuth flow.

    Args:
        client_id: GitHub OAuth app client ID
        scopes: List of OAuth scopes
        force_new: Force new authentication even if token exists

    Returns:
        str: GitHub access token
    """
    # Check for existing token unless force_new
    if not force_new:
        existing_token = load_token()
        if existing_token:
            print("✅ Using saved OAuth token\n")
            return existing_token

    # Start new OAuth flow
    flow = OAuthDeviceFlow(client_id=client_id, scopes=scopes)
    token = flow.authenticate()

    # Save token for future use
    save_token(token)

    return token


def main():
    """CLI interface for OAuth token management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage GitHub OAuth tokens for github-activity-reporter"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Authenticate and save new OAuth token"
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="Remove saved OAuth token"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check if OAuth token is saved"
    )
    parser.add_argument(
        "--client-id",
        help="Custom GitHub OAuth app client ID"
    )

    args = parser.parse_args()

    if args.logout:
        clear_token()
    elif args.login:
        get_or_create_token(client_id=args.client_id, force_new=True)
    elif args.status:
        token = load_token()
        if token:
            print(f"✅ OAuth token is saved at: {TOKEN_FILE}")
        else:
            print("❌ No OAuth token found. Run with --login to authenticate.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

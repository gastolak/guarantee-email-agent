#!/usr/bin/env python3
"""
Gmail OAuth Token Helper Script

This script helps you obtain a Gmail OAuth token for the warranty email agent.

Prerequisites:
1. Go to https://console.cloud.google.com/
2. Create a project (or select existing)
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the credentials.json file

Usage:
    python scripts/get_gmail_token.py --credentials path/to/credentials.json
"""

import argparse
import json
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]


def get_gmail_token(credentials_path: str, token_output_path: str = 'token.pickle'):
    """
    Get Gmail OAuth token using OAuth 2.0 flow.

    Args:
        credentials_path: Path to credentials.json from Google Cloud Console
        token_output_path: Where to save the token pickle file

    Returns:
        The OAuth token string
    """
    creds = None
    token_path = Path(token_output_path)

    # Check if we have a cached token
    if token_path.exists():
        print(f"📂 Found existing token at {token_path}")
        with open(token_path, 'rb') as token_file:
            creds = pickle.load(token_file)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("🔐 Starting OAuth flow...")
            print("📖 A browser window will open for authentication")

            if not Path(credentials_path).exists():
                print(f"❌ Error: Credentials file not found at {credentials_path}")
                print("\n📋 To get credentials.json:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Select/Create project")
                print("3. Enable Gmail API")
                print("4. Create OAuth 2.0 credentials (Desktop app)")
                print("5. Download JSON and save as credentials.json")
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            # Force offline access to get refresh_token
            creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

        # Save the credentials for future use
        with open(token_path, 'wb') as token_file:
            pickle.dump(creds, token_file)
        print(f"💾 Token saved to {token_path}")

    # Get the token string
    token_string = creds.token

    print("\n✅ Gmail OAuth Token obtained successfully!")
    print("\n📋 Add this to your .env file:")
    print(f"GMAIL_OAUTH_TOKEN={token_string}")
    print("\n" + "="*60)
    print(f"Token: {token_string[:50]}..." if len(token_string) > 50 else f"Token: {token_string}")
    print("="*60)

    return token_string


def main():
    parser = argparse.ArgumentParser(
        description='Get Gmail OAuth token for warranty email agent'
    )
    parser.add_argument(
        '--credentials',
        type=str,
        default='credentials.json',
        help='Path to credentials.json from Google Cloud Console'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='token.pickle',
        help='Where to save the token pickle file'
    )

    args = parser.parse_args()

    print("🔧 Gmail OAuth Token Helper")
    print("="*60)

    token = get_gmail_token(args.credentials, args.output)

    if token:
        print("\n✨ Next steps:")
        print("1. Copy the token above")
        print("2. Add to .env file: GMAIL_OAUTH_TOKEN=<token>")
        print("3. Run the agent: uv run python -m guarantee_email_agent run")
    else:
        print("\n❌ Failed to get token. Please check the instructions above.")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())

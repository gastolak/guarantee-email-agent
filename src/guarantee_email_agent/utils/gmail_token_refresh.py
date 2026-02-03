"""Gmail OAuth token refresh utility."""
import logging
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)


def refresh_gmail_token(token_pickle_path: str = "token.pickle") -> Optional[str]:
    """Refresh Gmail OAuth token from pickle file.

    Args:
        token_pickle_path: Path to token.pickle file

    Returns:
        Fresh OAuth access token, or None if refresh failed
    """
    token_path = Path(token_pickle_path)

    if not token_path.exists():
        logger.warning(
            f"Token pickle file not found at {token_path}",
            extra={"token_path": str(token_path)}
        )
        return None

    try:
        logger.info(
            "Loading Gmail credentials from pickle file",
            extra={"token_path": str(token_path)}
        )

        # Load credentials from pickle
        with open(token_path, 'rb') as token_file:
            creds: Credentials = pickle.load(token_file)

        # Check if credentials need refresh
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail token...")
                creds.refresh(Request())

                # Save refreshed credentials back to pickle
                with open(token_path, 'wb') as token_file:
                    pickle.dump(creds, token_file)

                logger.info(
                    "Gmail token refreshed successfully",
                    extra={"token_expires": creds.expiry.isoformat() if creds.expiry else None}
                )
            else:
                logger.error(
                    "Cannot refresh token - no refresh_token available",
                    extra={"has_creds": creds is not None, "has_refresh_token": creds.refresh_token if creds else None}
                )
                return None
        else:
            logger.info(
                "Gmail token is still valid",
                extra={"token_expires": creds.expiry.isoformat() if creds.expiry else None}
            )

        return creds.token

    except Exception as e:
        logger.error(
            f"Failed to refresh Gmail token: {e}",
            extra={"error": str(e), "token_path": str(token_path)}
        )
        return None


def get_fresh_gmail_token(
    token_pickle_path: str = "token.pickle",
    fallback_token: Optional[str] = None
) -> Optional[str]:
    """Get a fresh Gmail token, refreshing if needed.

    Args:
        token_pickle_path: Path to token.pickle file
        fallback_token: Fallback token from environment if pickle refresh fails

    Returns:
        Fresh OAuth access token, or fallback token if refresh failed
    """
    refreshed_token = refresh_gmail_token(token_pickle_path)

    if refreshed_token:
        return refreshed_token

    if fallback_token:
        logger.warning(
            "Using fallback token from environment (may be expired)",
            extra={"has_pickle": Path(token_pickle_path).exists()}
        )
        return fallback_token

    logger.error("No valid Gmail token available - neither refreshed nor fallback")
    return None

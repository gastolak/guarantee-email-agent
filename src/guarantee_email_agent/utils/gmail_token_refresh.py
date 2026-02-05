"""Gmail OAuth token refresh utility."""
import logging
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

# Refresh token if it expires within this threshold
TOKEN_REFRESH_THRESHOLD = timedelta(minutes=5)


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

        if not creds:
            logger.error("No credentials found in pickle file")
            return None

        # Check if token needs refresh (expired or expiring soon)
        needs_refresh = False
        if creds.expired:
            logger.info("Gmail token is expired")
            needs_refresh = True
        elif not creds.valid:
            logger.info("Gmail token is invalid")
            needs_refresh = True
        elif creds.expiry:
            # Make expiry timezone-aware if it isn't already
            expiry = creds.expiry
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            time_until_expiry = expiry - datetime.now(timezone.utc)
            if time_until_expiry < TOKEN_REFRESH_THRESHOLD:
                logger.info(
                    f"Gmail token expires soon (in {time_until_expiry.total_seconds():.0f}s), refreshing proactively",
                    extra={"expires_in_seconds": time_until_expiry.total_seconds()}
                )
                needs_refresh = True

        if needs_refresh:
            if not creds.refresh_token:
                logger.error("Cannot refresh token - no refresh_token available")
                return None

            logger.info("Refreshing Gmail token...")
            creds.refresh(Request())

            # Save refreshed credentials back to pickle
            with open(token_path, 'wb') as token_file:
                pickle.dump(creds, token_file)

            logger.info(
                "Gmail token refreshed successfully",
                extra={"token_expires": creds.expiry.isoformat() if creds.expiry else None}
            )
        else:
            if creds.expiry:
                expiry = creds.expiry
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                time_until_expiry = expiry - datetime.now(timezone.utc)
                logger.info(
                    f"Gmail token is still valid (expires in {time_until_expiry.total_seconds():.0f}s)",
                    extra={"token_expires": creds.expiry.isoformat()}
                )
            else:
                logger.info("Gmail token is still valid")

        return creds.token

    except Exception as e:
        logger.error(
            f"Failed to refresh Gmail token: {e}",
            extra={"error": str(e), "token_path": str(token_path)},
            exc_info=True
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

"""Agent runner with inbox monitoring and graceful shutdown.

Implements:
- AC: Monitor loop polls Gmail inbox
- AC: Processing loop continues until shutdown
- AC: Graceful shutdown on SIGTERM/SIGINT
- AC: In-flight emails completed before shutdown
- NFR10: Poll inbox every 60 seconds, concurrent processing
- NFR36: Graceful shutdown on signals
"""

import asyncio
import logging
import signal
import time
from typing import Any, Dict, List

from guarantee_email_agent.config.schema import AgentConfig
from guarantee_email_agent.email.processor import EmailProcessor
from guarantee_email_agent.email.processor_models import ProcessingResult
from guarantee_email_agent.tools import GmailTool
from guarantee_email_agent.utils.gmail_token_refresh import get_fresh_gmail_token

logger = logging.getLogger(__name__)


class AgentRunner:
    """Agent runner with inbox monitoring and graceful shutdown.

    Responsibilities:
    - Poll Gmail inbox at configured interval
    - Process emails concurrently through EmailProcessor
    - Handle SIGTERM/SIGINT for graceful shutdown
    - Track processing statistics
    - Clean up tool connections on shutdown
    """

    def __init__(self, config: AgentConfig, processor: EmailProcessor):
        """Initialize agent runner.

        Args:
            config: Agent configuration
            processor: Email processor
        """
        self.config = config
        self.processor = processor
        self.gmail_tool = processor.gmail_tool
        self.crm_abacus_tool = processor.crm_abacus_tool

        # State tracking
        self._shutdown_requested = False
        self._log_rotation_requested = False
        self._start_time = time.time()
        self._emails_processed = 0
        self._errors_count = 0
        self._consecutive_errors = 0

        # Configuration
        self.polling_interval = getattr(
            config.agent, 'polling_interval_seconds', 60
        )
        self.shutdown_timeout = 30  # seconds

        logger.info("Agent runner initialized")

    def register_signal_handlers(self):
        """Register signal handlers for graceful shutdown and log rotation.

        Handles:
        - SIGTERM: Graceful shutdown (systemd/Docker)
        - SIGINT: Graceful shutdown (Ctrl+C)
        - SIGHUP: Log rotation without interrupting operation
        """
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGHUP, self._handle_sighup)
        logger.info("Signal handlers registered (SIGTERM, SIGINT, SIGHUP)")

    def _handle_shutdown_signal(self, signum: int, frame):
        """Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"{signal_name} received, initiating graceful shutdown")
        self._shutdown_requested = True

    def _handle_sighup(self, signum: int, frame):
        """Handle SIGHUP for log rotation.

        Args:
            signum: Signal number (SIGHUP)
            frame: Current stack frame
        """
        logger.info("SIGHUP received, rotating log files")
        self._log_rotation_requested = True

    def _refresh_gmail_token(self) -> None:
        """Refresh Gmail OAuth token if needed.

        This is called before each inbox poll to ensure the token is always fresh.
        Tokens expire after ~1 hour, so we refresh them proactively.
        """
        try:
            fresh_token = get_fresh_gmail_token(
                token_pickle_path="token.pickle",
                fallback_token=self.config.secrets.gmail_oauth_token
            )

            if fresh_token and fresh_token != self.gmail_tool.oauth_token:
                logger.info("Updating Gmail tool with refreshed token")
                self.gmail_tool.oauth_token = fresh_token
            elif not fresh_token:
                logger.warning("Token refresh returned None - using existing token")
        except Exception as e:
            logger.error(f"Error refreshing Gmail token: {e}", exc_info=True)

    async def poll_inbox(self) -> List[Dict[str, Any]]:
        """Poll Gmail inbox for unread emails.

        Returns:
            List of raw email data

        Note:
            Errors are logged but don't crash the loop
        """
        try:
            logger.debug("Checking inbox...")
            # Use Gmail MCP client to monitor inbox
            emails = await self.gmail_tool.fetch_unread_emails()

            if emails:
                logger.info(f"Found {len(emails)} unread emails")
            else:
                logger.debug("No new emails")

            return emails

        except Exception as e:
            logger.error(f"Error polling inbox: {e}", exc_info=True)
            return []  # Return empty list on error (don't crash loop)

    async def process_inbox_emails(
        self,
        emails: List[Dict[str, Any]]
    ) -> List[ProcessingResult]:
        """Process multiple emails concurrently.

        Args:
            emails: List of raw email data

        Returns:
            List of processing results

        Note:
            Uses asyncio.gather() for concurrent processing (NFR10)
        """
        if not emails:
            return []

        logger.info(f"Processing {len(emails)} emails...")

        # Process emails concurrently
        tasks = [
            self.processor.process_email_with_functions(email)
            for email in emails
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                email_id = emails[i].get("id", "unknown")
                logger.error(
                    f"Email processing raised exception: {type(result).__name__}: {result}",
                    extra={"email_id": email_id},
                    exc_info=result
                )

        # Count successes and failures
        success_count = sum(
            1 for r in results
            if isinstance(r, ProcessingResult) and r.success
        )
        failed_count = len(results) - success_count

        logger.info(
            f"Processing complete: {success_count} succeeded, {failed_count} failed",
            extra={
                "emails_processed": len(emails),
                "success_count": success_count,
                "failed_count": failed_count
            }
        )

        # Update state
        self._emails_processed += len(emails)
        self._errors_count += failed_count

        if failed_count > 0:
            self._consecutive_errors += 1
        else:
            self._consecutive_errors = 0

        # Warn if many consecutive errors
        if self._consecutive_errors >= 10:
            logger.warning(
                f"High consecutive error count: {self._consecutive_errors} - "
                f"check MCP connections and configuration"
            )

        return [r for r in results if isinstance(r, ProcessingResult)]

    async def run_once(self) -> None:
        """Run agent once: poll inbox, process emails, and exit.

        Used for testing and one-time processing.
        """
        logger.info("Running in single-pass mode")

        # Connect to all MCP clients
        # Tools don't need explicit connection
        # Tools don't need explicit connection
        # Tools don't need explicit connection

        try:
            # Refresh Gmail token before polling
            self._refresh_gmail_token()

            # Poll inbox
            emails = await self.poll_inbox()

            # Process emails if any found
            if emails:
                await self.process_inbox_emails(emails)
            else:
                logger.info("No emails to process")

            # Log final status
            uptime = int(time.time() - self._start_time)
            logger.info(
                f"Single-pass complete: {self._emails_processed} emails processed, "
                f"{self._errors_count} errors, runtime: {uptime}s"
            )

        except Exception as e:
            logger.error(f"Error in single-pass run: {e}", exc_info=True)
            raise

    async def run(self) -> None:
        """Run main monitoring loop.

        Polls inbox at configured interval and processes emails until
        shutdown signal received.

        Loop will:
        - Check for log rotation requests (SIGHUP)
        - Poll inbox for unread emails
        - Process emails concurrently
        - Sleep for polling interval
        - Check shutdown flag
        - Exit gracefully on shutdown

        Note:
            Errors during processing don't crash the loop
        """
        logger.info("Agent starting (restart safe, idempotent)")
        logger.info("Entering monitoring loop")
        logger.info(f"Polling interval: {self.polling_interval}s")

        # Connect to all MCP clients
        # Tools don't need explicit connection
        # Tools don't need explicit connection
        # Tools don't need explicit connection

        try:
            while not self._shutdown_requested:
                # Check log rotation flag
                if self._log_rotation_requested:
                    self._rotate_logs()
                    self._log_rotation_requested = False

                # Refresh Gmail token before polling (tokens expire after ~1 hour)
                self._refresh_gmail_token()

                # Poll inbox
                emails = await self.poll_inbox()

                # Process emails if any found
                if emails:
                    await self.process_inbox_emails(emails)

                # Log periodic status (every 10 minutes or after processing)
                current_time = time.time()
                uptime = int(current_time - self._start_time)
                if emails or (uptime % 600 < self.polling_interval):
                    logger.info(
                        f"Status: {self._emails_processed} emails processed, "
                        f"{self._errors_count} errors, uptime: {uptime}s"
                    )

                # Check shutdown flag before sleeping
                if self._shutdown_requested:
                    break

                # Sleep until next poll
                await asyncio.sleep(self.polling_interval)

            # Shutdown requested
            logger.info("Shutdown flag set, exiting monitoring loop")
            await self._graceful_shutdown()

        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
            raise

    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown.

        Steps:
        - Wait for in-flight processing (max 30s)
        - Close MCP connections
        - Log final statistics
        """
        logger.info("Performing graceful shutdown...")

        # Note: In-flight processing already awaited in run() loop
        # This is where we'd wait for background tasks if any

        # Close MCP connections
        logger.info("Closing MCP connections...")
        try:
            await asyncio.wait_for(
                self._cleanup_connections(),
                timeout=self.shutdown_timeout
            )
            logger.info("✓ MCP connections closed")
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout exceeded, forcing cleanup")
            # Force cleanup even if timeout
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

        # Log final statistics
        uptime = int(time.time() - self._start_time)
        logger.info(
            f"Agent shutdown complete - "
            f"Uptime: {uptime}s, "
            f"Emails processed: {self._emails_processed}, "
            f"Errors: {self._errors_count}"
        )

    async def _cleanup_connections(self) -> None:
        """Close all MCP connections cleanly."""
        try:
            if hasattr(self.gmail_tool, 'close'):
                await self.gmail_tool.close()
        except Exception as e:
            logger.warning(f"Error closing Gmail client: {e}")

        try:
            if hasattr(self.crm_abacus_tool, 'close'):
                await self.crm_abacus_tool.close()
        except Exception as e:
            logger.warning(f"Error closing Warranty API client: {e}")

        try:
            # CRM Abacus already closed
                pass # CRM Abacus already closed
        except Exception as e:
            logger.warning(f"Error closing Ticketing client: {e}")

    def _rotate_logs(self) -> None:
        """Rotate log files by closing and reopening handlers.

        This method is called when SIGHUP is received. It closes all
        file handlers and reopens them, allowing external log rotation
        tools (like logrotate) to move/rename log files.

        Note:
            Compatible with logrotate utility (NFR32)
        """
        try:
            logger.info("Starting log rotation...")

            # Get root logger
            root_logger = logging.getLogger()

            # Store file paths and configurations before closing
            file_handlers = []
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    file_handlers.append({
                        'path': handler.baseFilename,
                        'level': handler.level,
                        'formatter': handler.formatter
                    })
                    handler.close()
                    root_logger.removeHandler(handler)

            # Recreate file handlers with same configuration
            for handler_config in file_handlers:
                new_handler = logging.FileHandler(handler_config['path'])
                new_handler.setLevel(handler_config['level'])
                new_handler.setFormatter(handler_config['formatter'])
                root_logger.addHandler(new_handler)

            logger.info("Log rotation complete")

        except Exception as e:
            logger.error(f"Error during log rotation: {e}", exc_info=True)

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
from guarantee_email_agent.integrations.mcp.gmail_client import GmailMCPClient

logger = logging.getLogger(__name__)


class AgentRunner:
    """Agent runner with inbox monitoring and graceful shutdown.

    Responsibilities:
    - Poll Gmail inbox at configured interval
    - Process emails concurrently through EmailProcessor
    - Handle SIGTERM/SIGINT for graceful shutdown
    - Track processing statistics
    - Clean up MCP connections on shutdown
    """

    def __init__(self, config: AgentConfig, processor: EmailProcessor):
        """Initialize agent runner.

        Args:
            config: Agent configuration
            processor: Email processor
        """
        self.config = config
        self.processor = processor
        self.gmail_client = processor.gmail_client

        # State tracking
        self._shutdown_requested = False
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
        """Register signal handlers for graceful shutdown.

        Handles:
        - SIGTERM: Graceful shutdown (systemd/Docker)
        - SIGINT: Graceful shutdown (Ctrl+C)
        """
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        logger.info("Signal handlers registered (SIGTERM, SIGINT)")

    def _handle_shutdown_signal(self, signum: int, frame):
        """Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"Shutdown requested via {signal_name}")
        self._shutdown_requested = True

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
            emails = await self.gmail_client.monitor_inbox()

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
            self.processor.process_email(email)
            for email in emails
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

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
        await self.gmail_client.connect()
        await self.processor.warranty_client.connect()
        await self.processor.ticketing_client.connect()

        try:
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
        - Poll inbox for unread emails
        - Process emails concurrently
        - Sleep for polling interval
        - Check shutdown flag
        - Exit gracefully on shutdown

        Note:
            Errors during processing don't crash the loop
        """
        logger.info("Entering monitoring loop")
        logger.info(f"Polling interval: {self.polling_interval}s")

        # Connect to all MCP clients
        await self.gmail_client.connect()
        await self.processor.warranty_client.connect()
        await self.processor.ticketing_client.connect()

        try:
            while not self._shutdown_requested:
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
            if hasattr(self.processor.gmail_client, 'close'):
                await self.processor.gmail_client.close()
        except Exception as e:
            logger.warning(f"Error closing Gmail client: {e}")

        try:
            if hasattr(self.processor.warranty_client, 'close'):
                await self.processor.warranty_client.close()
        except Exception as e:
            logger.warning(f"Error closing Warranty API client: {e}")

        try:
            if hasattr(self.processor.ticketing_client, 'close'):
                await self.processor.ticketing_client.close()
        except Exception as e:
            logger.warning(f"Error closing Ticketing client: {e}")

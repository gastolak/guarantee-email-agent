"""
Supabase Logger for Warranty Email Agent

Logs all agent activity (email sessions, steps, function calls, responses) to Supabase.
Implements PII compliance, selective prompt storage, and async non-blocking logging.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseLogger:
    """
    Async logger for warranty email agent telemetry.

    Features:
    - PII-compliant: No full email bodies stored
    - Async: Non-blocking logging operations
    - Selective storage: Full LLM prompts only for failures
    - Data retention: Configurable auto-cleanup period
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        retention_days: int = 30,
        store_full_prompts: bool = False,
        logging_required: bool = False,
        agent_version: str = "1.0.0",
    ):
        """
        Initialize Supabase logger.

        Args:
            supabase_url: Supabase project URL (or SUPABASE_URL env var)
            supabase_key: Supabase anon key (or SUPABASE_KEY env var)
            retention_days: Auto-delete logs older than N days (default: 30)
            store_full_prompts: Store full LLM prompts for success (default: False)
            logging_required: Crash agent if Supabase unavailable (default: False)
            agent_version: Agent version for telemetry (default: "1.0.0")
        """
        self.retention_days = retention_days
        self.store_full_prompts = store_full_prompts
        self.logging_required = logging_required
        self.agent_version = agent_version

        # Get credentials from args or environment
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")

        # Check if logging is enabled
        self.enabled = bool(self.supabase_url and self.supabase_key)

        if not self.enabled:
            if self.logging_required:
                raise ValueError(
                    "Supabase logging required but SUPABASE_URL or SUPABASE_KEY not set"
                )
            logger.warning(
                "Supabase logging disabled: SUPABASE_URL or SUPABASE_KEY not set"
            )
            self.client = None
            return

        # Initialize Supabase client
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info(f"Supabase logger initialized (retention: {retention_days} days)")
        except Exception as e:
            if self.logging_required:
                raise ValueError(f"Failed to initialize Supabase client: {e}") from e
            logger.error(f"Supabase initialization failed: {e}", exc_info=True)
            self.enabled = False
            self.client = None

    def _handle_error(self, operation: str, error: Exception) -> None:
        """
        Handle logging errors gracefully.

        Args:
            operation: Operation that failed (e.g., "log_email_session_start")
            error: Exception that occurred
        """
        logger.error(f"Supabase logging failed ({operation}): {error}", exc_info=True)
        if self.logging_required:
            raise

    @staticmethod
    def _hash_text(text: str) -> str:
        """Generate SHA-256 hash of text for deduplication."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    async def test_connection(self) -> bool:
        """
        Test Supabase connection by attempting a simple query.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Test query: count email_sessions
            result = self.client.table("email_sessions").select("session_id", count="exact").limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            self._handle_error("test_connection", e)
            return False

    async def log_email_session_start(
        self,
        email_id: str,
        from_address: str,
        email_subject: str,
        email_body: str,
        received_at: datetime,
        model_provider: str,
        model_name: str,
    ) -> Optional[str]:
        """
        Log start of email processing session.

        Args:
            email_id: Gmail message ID
            from_address: Sender email address
            email_subject: Email subject line
            email_body: Full email body (NOT stored, only hashed)
            received_at: Email received timestamp
            model_provider: LLM provider ('gemini', 'anthropic')
            model_name: Model name (e.g., 'gemini-2.0-flash')

        Returns:
            session_id (UUID string) or None if logging disabled/failed
        """
        if not self.enabled:
            return None

        try:
            # Calculate PII-safe metadata
            email_body_hash = self._hash_text(email_body)
            email_body_length = len(email_body)
            expires_at = datetime.now() + timedelta(days=self.retention_days)

            data = {
                "email_id": email_id,
                "from_address": from_address,
                "email_subject": email_subject,
                "email_body_hash": email_body_hash,
                "email_body_length": email_body_length,
                "received_at": received_at.isoformat(),
                "status": "processing",
                "agent_version": self.agent_version,
                "model_provider": model_provider,
                "model_name": model_name,
                "expires_at": expires_at.isoformat(),
            }

            result = self.client.table("email_sessions").insert(data).execute()
            session_id = result.data[0]["session_id"]
            logger.debug(f"Email session started: {session_id}")
            return session_id

        except Exception as e:
            self._handle_error("log_email_session_start", e)
            return None

    async def log_email_session_complete(
        self,
        session_id: str,
        status: str,
        outcome: Optional[str] = None,
        ticket_id: Optional[str] = None,
        serial_number: Optional[str] = None,
        issue_category: Optional[str] = None,
        total_steps: int = 0,
        step_sequence: Optional[List[str]] = None,
        total_duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Log completion of email processing session.

        Args:
            session_id: Session UUID from log_email_session_start
            status: Final status ('completed', 'failed', 'halted')
            outcome: Outcome type ('ticket_created', 'ai_opt_out', 'escalated', etc.)
            ticket_id: Created ticket ID (if applicable)
            serial_number: Extracted serial number (if found)
            issue_category: Classified issue category
            total_steps: Number of steps executed
            step_sequence: List of step names executed
            total_duration_ms: Total processing time in milliseconds
            error_message: Error message if failed

        Returns:
            True if logged successfully, False otherwise
        """
        if not self.enabled or not session_id:
            return False

        try:
            update_data = {
                "status": status,
                "completed_at": datetime.now().isoformat(),
                "total_steps": total_steps,
                "logs_finalized": True,  # Mark logs as complete
            }

            # Add optional fields if provided
            if outcome:
                update_data["outcome"] = outcome
            if ticket_id:
                update_data["ticket_id"] = ticket_id
            if serial_number:
                update_data["serial_number"] = serial_number
            if issue_category:
                update_data["issue_category"] = issue_category
            if step_sequence:
                update_data["step_sequence"] = step_sequence
            if total_duration_ms is not None:
                update_data["total_duration_ms"] = total_duration_ms
            if error_message:
                update_data["error_message"] = error_message

            self.client.table("email_sessions").update(update_data).eq("session_id", session_id).execute()
            logger.debug(f"Email session completed: {session_id} ({status})")
            return True

        except Exception as e:
            self._handle_error("log_email_session_complete", e)
            return False

    async def log_step_start(
        self,
        session_id: str,
        step_number: int,
        step_name: str,
        input_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Log start of step execution.

        Args:
            session_id: Parent email session UUID
            step_number: Step number (1, 2, 3...)
            step_name: Step name (e.g., '01-extract-serial')
            input_context: Context data (serial_number, ticket_id, etc.)

        Returns:
            execution_id (UUID string) or None if logging disabled/failed
        """
        if not self.enabled or not session_id:
            return None

        try:
            data = {
                "session_id": session_id,
                "step_number": step_number,
                "step_name": step_name,
                "status": "success",  # Will be updated on completion
            }

            # Add input context if provided
            if input_context:
                # Store only summary (key fields, not full context)
                summary = {
                    k: v for k, v in input_context.items()
                    if k in ["serial_number", "ticket_id", "email_id", "from_address"]
                }
                data["input_context_summary"] = summary

            result = self.client.table("step_executions").insert(data).execute()
            execution_id = result.data[0]["execution_id"]
            logger.debug(f"Step started: {step_name} ({execution_id})")
            return execution_id

        except Exception as e:
            self._handle_error("log_step_start", e)
            return None

    async def log_step_complete(
        self,
        execution_id: str,
        llm_prompt: Optional[str] = None,
        llm_response: Optional[str] = None,
        llm_token_count: Optional[int] = None,
        parsed_output: Optional[Dict[str, Any]] = None,
        next_step: Optional[str] = None,
        routing_reason: Optional[str] = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Log completion of step execution.

        Implements selective prompt storage: Full prompts ONLY for failures
        (unless store_full_prompts=True in config).

        Args:
            execution_id: Execution UUID from log_step_start
            llm_prompt: Full LLM prompt text
            llm_response: Full LLM response text
            llm_token_count: Token count for cost analysis
            parsed_output: Structured output (serial_number, next_step, etc.)
            next_step: Next step name
            routing_reason: Routing decision reason
            duration_ms: Step execution time in milliseconds
            status: Status ('success', 'failed', 'timeout')
            error_message: Error message if failed

        Returns:
            True if logged successfully, False otherwise
        """
        if not self.enabled or not execution_id:
            return False

        try:
            update_data = {
                "completed_at": datetime.now().isoformat(),
                "status": status,
            }

            # Selective prompt storage: full prompts only for failures
            store_prompts = status != "success" or self.store_full_prompts

            if llm_prompt:
                update_data["llm_prompt_hash"] = self._hash_text(llm_prompt)
                if store_prompts:
                    update_data["llm_prompt"] = llm_prompt

            if llm_response and store_prompts:
                update_data["llm_response"] = llm_response

            # Add optional fields
            if llm_token_count is not None:
                update_data["llm_token_count"] = llm_token_count
            if parsed_output:
                update_data["parsed_output"] = parsed_output
            if next_step:
                update_data["next_step"] = next_step
            if routing_reason:
                update_data["routing_reason"] = routing_reason
            if duration_ms is not None:
                update_data["duration_ms"] = duration_ms
            if error_message:
                update_data["error_message"] = error_message

            self.client.table("step_executions").update(update_data).eq("execution_id", execution_id).execute()
            logger.debug(f"Step completed: {execution_id} ({status})")
            return True

        except Exception as e:
            self._handle_error("log_step_complete", e)
            return False

    async def log_function_call_start(
        self,
        execution_id: str,
        session_id: str,
        function_name: str,
        function_args: Dict[str, Any],
    ) -> Optional[str]:
        """
        Log start of function call.

        Args:
            execution_id: Parent step execution UUID
            session_id: Parent email session UUID
            function_name: Function name ('check_warranty', 'create_ticket', etc.)
            function_args: Function arguments as dict

        Returns:
            call_id (UUID string) or None if logging disabled/failed
        """
        if not self.enabled or not execution_id or not session_id:
            return None

        try:
            data = {
                "execution_id": execution_id,
                "session_id": session_id,
                "function_name": function_name,
                "function_args": function_args,
                "status": "success",  # Will be updated on completion
            }

            result = self.client.table("function_calls").insert(data).execute()
            call_id = result.data[0]["call_id"]
            logger.debug(f"Function call started: {function_name} ({call_id})")
            return call_id

        except Exception as e:
            self._handle_error("log_function_call_start", e)
            return None

    async def log_function_call_complete(
        self,
        call_id: str,
        function_response: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        retry_count: int = 0,
    ) -> bool:
        """
        Log completion of function call.

        Args:
            call_id: Call UUID from log_function_call_start
            function_response: Function response as dict
            duration_ms: Call duration in milliseconds
            status: Status ('success', 'failed', 'timeout')
            error_message: Error message if failed
            retry_count: Number of retries attempted

        Returns:
            True if logged successfully, False otherwise
        """
        if not self.enabled or not call_id:
            return False

        try:
            update_data = {
                "completed_at": datetime.now().isoformat(),
                "status": status,
                "retry_count": retry_count,
            }

            if function_response:
                update_data["function_response"] = function_response
            if duration_ms is not None:
                update_data["duration_ms"] = duration_ms
            if error_message:
                update_data["error_message"] = error_message

            self.client.table("function_calls").update(update_data).eq("call_id", call_id).execute()
            logger.debug(f"Function call completed: {call_id} ({status})")
            return True

        except Exception as e:
            self._handle_error("log_function_call_complete", e)
            return False

    async def log_email_response(
        self,
        session_id: str,
        recipient_type: str,
        recipient_email: str,
        subject: str,
        body: str,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        status: str = "sent",
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log email response sent by agent.

        PII-compliant: Full email body NOT stored, only template info.

        Args:
            session_id: Parent email session UUID
            recipient_type: Recipient type ('customer', 'admin', 'supervisor')
            recipient_email: Recipient email address
            subject: Email subject line
            body: Full email body (NOT stored, only length calculated)
            template_name: Template name (e.g., 'device-not-found')
            template_variables: Template variables (ticket_id, serial_number, etc.)
            status: Status ('sent', 'failed')
            error_message: Error message if failed

        Returns:
            response_id (UUID string) or None if logging disabled/failed
        """
        if not self.enabled or not session_id:
            return None

        try:
            data = {
                "session_id": session_id,
                "recipient_type": recipient_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "body_length": len(body),  # Store length, not full body
                "status": status,
            }

            if template_name:
                data["template_name"] = template_name
            if template_variables:
                data["template_variables"] = template_variables
            if error_message:
                data["error_message"] = error_message

            result = self.client.table("email_responses").insert(data).execute()
            response_id = result.data[0]["response_id"]
            logger.debug(f"Email response logged: {response_id} ({recipient_type})")
            return response_id

        except Exception as e:
            self._handle_error("log_email_response", e)
            return None

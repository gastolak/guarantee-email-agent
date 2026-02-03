"""Function dispatcher for routing LLM function calls to tools.

This module provides the FunctionDispatcher class that routes function calls
from the LLM to the appropriate tool methods.
"""

import logging
import time
from typing import Any, Dict, Optional

from guarantee_email_agent.llm.function_calling import FunctionCall
from guarantee_email_agent.tools import GmailTool, CrmAbacusTool

logger = logging.getLogger(__name__)


class FunctionDispatcher:
    """Dispatch function calls from LLM to appropriate tools.

    Maps function names to tool methods and handles execution with
    logging, timing, and error handling.

    Attributes:
        gmail_tool: Gmail tool for email operations
        crm_abacus_tool: CRM Abacus tool for warranty and ticketing
    """

    def __init__(
        self,
        gmail_tool: Optional[GmailTool] = None,
        crm_abacus_tool: Optional[CrmAbacusTool] = None,
        supabase_logger: Optional["SupabaseLogger"] = None
    ):
        """Initialize FunctionDispatcher with tool instances.

        Args:
            gmail_tool: Gmail tool for email operations
            crm_abacus_tool: CRM Abacus tool for warranty and ticketing
            supabase_logger: Optional SupabaseLogger for telemetry (Story 5.3)
        """
        self._gmail_tool = gmail_tool
        self._crm_abacus_tool = crm_abacus_tool
        self.supabase_logger = supabase_logger

        logger.info(
            "FunctionDispatcher initialized",
            extra={
                "has_gmail_tool": gmail_tool is not None,
                "has_crm_abacus_tool": crm_abacus_tool is not None,
                "supabase_logging_enabled": supabase_logger.enabled if supabase_logger else False
            }
        )

    async def execute(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        session_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> FunctionCall:
        """Execute a function call and return the result.

        Routes the function call to the appropriate client method,
        tracks execution time, and returns a FunctionCall record.

        Args:
            function_name: Name of function to call
            arguments: Function arguments as dictionary
            session_id: Supabase session ID for telemetry (Story 5.3)
            execution_id: Supabase execution ID for telemetry (Story 5.3)

        Returns:
            FunctionCall with result and execution metadata

        Raises:
            ValueError: If function_name is unknown
        """
        start_time = time.time()

        # Story 5.3: Log function call start
        call_id = None
        if self.supabase_logger and session_id and execution_id:
            call_id = await self.supabase_logger.log_function_call_start(
                execution_id=execution_id,
                session_id=session_id,
                function_name=function_name,
                function_args=arguments
            )

        logger.info(
            "Executing function",
            extra={
                "function": function_name,
                "arguments": arguments
            }
        )

        # Check for unknown function first - this should raise immediately
        if function_name not in ("check_warranty", "create_ticket", "send_email"):
            raise ValueError(f"Unknown function: {function_name}")

        try:
            if function_name == "check_warranty":
                result = await self._execute_check_warranty(arguments)
            elif function_name == "create_ticket":
                result = await self._execute_create_ticket(arguments)
            elif function_name == "send_email":
                result = await self._execute_send_email(arguments)

            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Function executed successfully",
                extra={
                    "function": function_name,
                    "execution_time_ms": execution_time_ms,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else None
                }
            )

            # Story 5.3: Log function call completion (success)
            if self.supabase_logger and call_id:
                await self.supabase_logger.log_function_call_complete(
                    call_id=call_id,
                    function_response=result if isinstance(result, dict) else {"result": str(result)},
                    duration_ms=execution_time_ms,
                    status="success",
                    error_message=None,
                    retry_count=0  # TODO: Track retries from tenacity
                )

            return FunctionCall(
                function_name=function_name,
                arguments=arguments,
                result=result,
                execution_time_ms=execution_time_ms,
                success=True
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "Function execution failed",
                extra={
                    "function": function_name,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms
                },
                exc_info=True
            )

            # Story 5.3: Log function call completion (failure)
            if self.supabase_logger and call_id:
                await self.supabase_logger.log_function_call_complete(
                    call_id=call_id,
                    function_response=None,
                    duration_ms=execution_time_ms,
                    status="failed",
                    error_message=str(e),
                    retry_count=0  # TODO: Track retries from tenacity
                )

            return FunctionCall(
                function_name=function_name,
                arguments=arguments,
                result={},
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(e)
            )

    async def _execute_check_warranty(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute check_warranty function.

        Args:
            arguments: Must contain 'serial_number'

        Returns:
            Warranty status result

        Raises:
            ValueError: If CRM Abacus tool not configured or serial_number missing
        """
        if self._crm_abacus_tool is None:
            raise ValueError("CRM Abacus tool not configured")

        serial_number = arguments.get("serial_number")
        if not serial_number:
            raise ValueError("Missing required argument: serial_number")

        result = await self._crm_abacus_tool.check_warranty(serial_number)
        return result

    async def _execute_create_ticket(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create_ticket function.

        Args:
            arguments: Must contain 'subject', 'description'; optional 'customer_email', 'priority'

        Returns:
            Ticket creation result with ticket_id

        Raises:
            ValueError: If CRM Abacus tool not configured or required args missing
        """
        if self._crm_abacus_tool is None:
            raise ValueError("CRM Abacus tool not configured")

        subject = arguments.get("subject")
        description = arguments.get("description")
        customer_email = arguments.get("customer_email")
        priority = arguments.get("priority")

        if not subject:
            raise ValueError("Missing required argument: subject")
        if not description:
            raise ValueError("Missing required argument: description")

        ticket_id = await self._crm_abacus_tool.create_ticket(
            subject=subject,
            description=description,
            customer_email=customer_email,
            priority=priority
        )

        return {
            "ticket_id": ticket_id,
            "status": "created"
        }

    async def _execute_send_email(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send_email function.

        Args:
            arguments: Must contain 'to', 'subject', 'body'; optional 'thread_id'

        Returns:
            Email send result with message_id and status

        Raises:
            ValueError: If Gmail tool not configured or required args missing
        """
        if self._gmail_tool is None:
            raise ValueError("Gmail tool not configured")

        to = arguments.get("to")
        subject = arguments.get("subject")
        body = arguments.get("body")
        thread_id = arguments.get("thread_id")

        if not to:
            raise ValueError("Missing required argument: to")
        if not subject:
            raise ValueError("Missing required argument: subject")
        if not body:
            raise ValueError("Missing required argument: body")

        message_id = await self._gmail_tool.send_email(
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id
        )

        return {
            "message_id": message_id,
            "status": "sent"
        }

    def get_available_functions(self) -> list[str]:
        """Get list of available function names based on configured tools.

        Returns:
            List of function names that can be executed
        """
        available = []
        if self._crm_abacus_tool is not None:
            available.extend(["check_warranty", "create_ticket"])
        if self._gmail_tool is not None:
            available.append("send_email")
        return available

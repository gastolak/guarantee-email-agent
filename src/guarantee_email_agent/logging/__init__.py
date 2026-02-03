"""
Supabase Activity Logging Module

This module provides telemetry logging for the warranty email agent.
All agent activity (emails, steps, function calls, responses) is logged to Supabase.

Key Features:
- PII-compliant: No full email bodies stored
- Async: Non-blocking logging
- Selective storage: Full LLM prompts only for failures
- Data retention: Auto-cleanup after configurable period
"""

from guarantee_email_agent.logging.supabase_logger import SupabaseLogger

__all__ = ["SupabaseLogger"]

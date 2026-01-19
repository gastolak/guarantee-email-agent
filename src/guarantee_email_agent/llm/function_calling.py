"""Function calling data models for LLM providers.

This module defines the data structures for LLM function calling:
- FunctionDefinition: Describes a function the LLM can call
- FunctionCall: Records a single function execution
- FunctionCallingResult: Complete result from function-calling generation
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class FunctionDefinition:
    """Function definition for LLM function-calling.

    Describes a function that the LLM can choose to call, including its
    name, description, and parameter schema.

    Attributes:
        name: Function identifier (e.g., "check_warranty")
        description: What the function does (helps LLM decide when to call)
        parameters: JSON Schema for function parameters
    """

    name: str
    description: str
    parameters: Dict[str, Any]

    def to_gemini_tool(self) -> Dict[str, Any]:
        """Convert to Gemini FunctionDeclaration format.

        Returns:
            Dictionary compatible with google.generativeai FunctionDeclaration
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


@dataclass(frozen=True)
class FunctionCall:
    """Record of a function call execution.

    Tracks a single function call made by the LLM, including the arguments
    passed, the result returned, and execution metadata.

    Attributes:
        function_name: Name of the function called
        arguments: Arguments passed to the function
        result: Result returned by the function
        execution_time_ms: How long the function took to execute
        success: Whether the function executed successfully
        error_message: Error message if execution failed
    """

    function_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    execution_time_ms: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class FunctionCallingResult:
    """Result from LLM generation with function calling.

    Contains the final response text, all function calls made during
    the multi-turn conversation, and metadata about the interaction.

    Attributes:
        response_text: Final text response from the LLM
        function_calls: List of all functions called during generation
        total_turns: Number of conversation turns (user + function responses)
        email_sent: True if send_email was called successfully
    """

    response_text: str
    function_calls: List[FunctionCall] = field(default_factory=list)
    total_turns: int = 1
    email_sent: bool = False

    def get_function_call(self, function_name: str) -> Optional[FunctionCall]:
        """Get the first function call with the given name.

        Args:
            function_name: Name of the function to find

        Returns:
            FunctionCall if found, None otherwise
        """
        for fc in self.function_calls:
            if fc.function_name == function_name:
                return fc
        return None

    def get_all_function_calls(self, function_name: str) -> List[FunctionCall]:
        """Get all function calls with the given name.

        Args:
            function_name: Name of the function to find

        Returns:
            List of matching FunctionCalls (may be empty)
        """
        return [fc for fc in self.function_calls if fc.function_name == function_name]

    def has_function_call(self, function_name: str) -> bool:
        """Check if a function was called.

        Args:
            function_name: Name of the function to check

        Returns:
            True if the function was called at least once
        """
        return any(fc.function_name == function_name for fc in self.function_calls)

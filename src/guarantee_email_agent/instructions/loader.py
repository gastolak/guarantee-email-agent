"""Instruction file loader with YAML frontmatter + XML body parsing."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter

from guarantee_email_agent.utils.errors import (
    InstructionParseError,
    InstructionValidationError,
)

logger = logging.getLogger(__name__)

# Global instruction cache
_instruction_cache: Dict[str, "InstructionFile"] = {}


def _validate_functions(
    functions: List[Dict[str, Any]],
    file_path: str
) -> List[Dict[str, Any]]:
    """Validate function definitions from YAML frontmatter.

    Args:
        functions: List of function definition dicts from YAML
        file_path: Path to instruction file (for error messages)

    Returns:
        Validated list of function definitions

    Raises:
        InstructionValidationError: If function definition is invalid
    """
    if not isinstance(functions, list):
        raise InstructionValidationError(
            message=f"available_functions must be a list in {file_path}",
            code="instruction_invalid_functions",
            details={"file_path": file_path}
        )

    validated = []
    for i, func in enumerate(functions):
        if not isinstance(func, dict):
            raise InstructionValidationError(
                message=f"Function {i} must be a dict in {file_path}",
                code="instruction_invalid_function",
                details={"file_path": file_path, "index": i}
            )

        # Validate required fields
        if "name" not in func:
            raise InstructionValidationError(
                message=f"Function {i} missing 'name' in {file_path}",
                code="instruction_function_missing_name",
                details={"file_path": file_path, "index": i}
            )

        if "description" not in func:
            raise InstructionValidationError(
                message=f"Function '{func.get('name', i)}' missing 'description' in {file_path}",
                code="instruction_function_missing_description",
                details={"file_path": file_path, "function": func.get("name", i)}
            )

        # Validate parameters if present
        parameters = func.get("parameters", {"type": "object", "properties": {}})
        if not isinstance(parameters, dict):
            raise InstructionValidationError(
                message=f"Function '{func['name']}' parameters must be a dict in {file_path}",
                code="instruction_function_invalid_params",
                details={"file_path": file_path, "function": func["name"]}
            )

        # Ensure parameters has required structure
        if "type" not in parameters:
            parameters["type"] = "object"
        if "properties" not in parameters:
            parameters["properties"] = {}

        validated.append({
            "name": func["name"],
            "description": func["description"],
            "parameters": parameters
        })

        logger.debug(
            f"Validated function: {func['name']}",
            extra={"function": func["name"], "file_path": file_path}
        )

    return validated


@dataclass
class InstructionFile:
    """Parsed instruction file with YAML frontmatter + XML body.

    Attributes:
        name: Instruction identifier (e.g., "main-orchestration")
        description: Human-readable description of instruction
        trigger: Optional trigger condition for scenario instructions
        version: Instruction version for tracking
        body: XML content for LLM processing
        file_path: Absolute path to instruction file
        available_functions: List of function definitions for LLM function calling
    """
    name: str
    description: str
    trigger: Optional[str]
    version: str
    body: str
    file_path: str
    available_functions: List[Dict[str, Any]] = field(default_factory=list)

    def get_available_functions(self) -> List["FunctionDefinition"]:
        """Get function definitions for LLM function calling.

        Returns:
            List of FunctionDefinition objects for use with LLM providers
        """
        from guarantee_email_agent.llm.function_calling import FunctionDefinition

        functions = []
        for func_data in self.available_functions:
            functions.append(FunctionDefinition(
                name=func_data["name"],
                description=func_data["description"],
                parameters=func_data.get("parameters", {"type": "object", "properties": {}})
            ))
        return functions

    def has_functions(self) -> bool:
        """Check if this instruction has function definitions.

        Returns:
            True if functions are defined, False otherwise
        """
        return len(self.available_functions) > 0


def load_instruction(file_path: str) -> InstructionFile:
    """Load and parse instruction file with YAML frontmatter + XML body.

    Args:
        file_path: Path to instruction .md file

    Returns:
        Parsed InstructionFile

    Raises:
        InstructionParseError: If YAML or XML malformed
        InstructionValidationError: If required fields missing
    """
    try:
        # Parse frontmatter + content
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Extract frontmatter fields
        metadata = post.metadata

        # Validate required fields
        required = ['name', 'description', 'version']
        for field in required:
            if field not in metadata:
                raise InstructionValidationError(
                    message=f"Missing required field '{field}' in {file_path}",
                    code="instruction_missing_field",
                    details={"file_path": file_path, "field": field}
                )

        # Extract body (XML content)
        body = post.content.strip()
        if not body:
            raise InstructionValidationError(
                message=f"Instruction body is empty in {file_path}",
                code="instruction_empty_body",
                details={"file_path": file_path}
            )

        # Optional XML validation
        try:
            # Try parsing as XML (if it has XML tags)
            if body.startswith('<'):
                ET.fromstring(f"<root>{body}</root>")
        except ET.ParseError as e:
            raise InstructionParseError(
                message=f"Malformed XML in {file_path}: {str(e)}",
                code="instruction_malformed_xml",
                details={"file_path": file_path, "error": str(e)}
            )

        # Validate version format (must be non-empty string)
        if not metadata['version']:
            raise InstructionValidationError(
                message=f"Version field is empty in {file_path}",
                code="instruction_invalid_version",
                details={"file_path": file_path}
            )

        # Parse available_functions if present
        available_functions = metadata.get('available_functions', [])
        if available_functions:
            available_functions = _validate_functions(available_functions, file_path)

        return InstructionFile(
            name=metadata['name'],
            description=metadata['description'],
            trigger=metadata.get('trigger'),
            version=metadata['version'],
            body=body,
            file_path=str(Path(file_path).resolve()),
            available_functions=available_functions
        )

    except FileNotFoundError:
        raise InstructionParseError(
            message=f"Instruction file not found: {file_path}",
            code="instruction_file_not_found",
            details={"file_path": file_path}
        )
    except Exception as e:
        if isinstance(e, (InstructionParseError, InstructionValidationError)):
            raise
        raise InstructionParseError(
            message=f"Failed to parse instruction file {file_path}: {str(e)}",
            code="instruction_parse_failed",
            details={"file_path": file_path, "error": str(e)}
        )


def load_instruction_cached(file_path: str) -> InstructionFile:
    """Load instruction with caching for performance.

    Args:
        file_path: Path to instruction file

    Returns:
        Parsed InstructionFile (from cache or freshly loaded)
    """
    # Normalize to absolute path for cache key
    abs_path = str(Path(file_path).resolve())

    # Check cache
    if abs_path in _instruction_cache:
        logger.debug(f"Instruction loaded from cache: {abs_path}")
        return _instruction_cache[abs_path]

    # Load and cache
    instruction = load_instruction(abs_path)
    _instruction_cache[abs_path] = instruction
    logger.info(
        f"Instruction loaded and cached: {instruction.name} v{instruction.version}",
        extra={
            "instruction_name": instruction.name,
            "instruction_version": instruction.version,
            "file_path": abs_path,
            "body_size": len(instruction.body)
        }
    )

    return instruction


def clear_instruction_cache() -> None:
    """Clear instruction cache (useful for testing and hot-reloading)."""
    _instruction_cache.clear()
    logger.debug("Instruction cache cleared")


def load_step_instruction(step_name: str) -> InstructionFile:
    """Load step instruction from instructions/steps/ directory.

    Args:
        step_name: Step name without path (e.g., "extract-serial")

    Returns:
        Parsed InstructionFile for the step

    Raises:
        InstructionParseError: If step file not found or malformed
    """
    # Construct path to step file
    # Assumes step files are in {project_root}/instructions/steps/
    from pathlib import Path
    import os

    # Get project root (assuming we're in src/guarantee_email_agent/...)
    current_file = Path(__file__)  # loader.py
    project_root = current_file.parent.parent.parent.parent  # Go up to project root

    # Construct step file path
    step_file_path = project_root / "instructions" / "steps" / f"{step_name}.md"

    logger.debug(
        f"Loading step instruction: {step_name}",
        extra={"step_name": step_name, "file_path": str(step_file_path)}
    )

    # Use cached loader for performance
    return load_instruction_cached(str(step_file_path))


def validate_instruction(instruction: InstructionFile) -> None:
    """Validate instruction structure and content.

    Args:
        instruction: Instruction to validate

    Raises:
        InstructionValidationError: If validation fails
    """
    # Validate required fields
    if not instruction.name:
        raise InstructionValidationError(
            message="Instruction name is empty",
            code="instruction_invalid_name",
            details={"file_path": instruction.file_path}
        )

    if not instruction.version:
        raise InstructionValidationError(
            message="Instruction version is empty",
            code="instruction_invalid_version",
            details={"file_path": instruction.file_path}
        )

    if not instruction.body:
        raise InstructionValidationError(
            message="Instruction body is empty",
            code="instruction_empty_body",
            details={"file_path": instruction.file_path}
        )

    # Validate filename follows kebab-case
    filename = Path(instruction.file_path).stem
    if '_' in filename:
        logger.warning(
            f"Instruction filename should use kebab-case, not snake_case: {filename}",
            extra={"file_path": instruction.file_path, "filename": filename}
        )

    logger.debug(f"Instruction validated: {instruction.name} v{instruction.version}")

"""Unit tests for instruction loader."""

import pytest
from pathlib import Path

from guarantee_email_agent.instructions.loader import (
    InstructionFile,
    load_instruction,
    load_instruction_cached,
    load_step_instruction,
    clear_instruction_cache,
    validate_instruction,
)
from guarantee_email_agent.utils.errors import (
    InstructionParseError,
    InstructionValidationError,
)


def test_load_instruction_valid(tmp_path: Path):
    """Test loading a valid instruction file with YAML frontmatter and XML body."""
    # Create valid instruction file
    instruction_file = tmp_path / "test-instruction.md"
    instruction_file.write_text("""---
name: test-instruction
description: Test instruction file
trigger: test_trigger
version: 1.0.0
---

<objective>
Test objective content
</objective>

<workflow>
Step 1: Do something
Step 2: Do something else
</workflow>
""")

    # Load instruction
    instruction = load_instruction(str(instruction_file))

    # Verify parsed fields
    assert instruction.name == "test-instruction"
    assert instruction.description == "Test instruction file"
    assert instruction.trigger == "test_trigger"
    assert instruction.version == "1.0.0"
    assert "<objective>" in instruction.body
    assert "<workflow>" in instruction.body
    assert instruction.file_path == str(instruction_file.resolve())


def test_load_instruction_missing_name(tmp_path: Path):
    """Test loading instruction file with missing 'name' field."""
    instruction_file = tmp_path / "missing-name.md"
    instruction_file.write_text("""---
description: Missing name field
version: 1.0.0
---

<objective>Test</objective>
""")

    with pytest.raises(InstructionValidationError) as exc_info:
        load_instruction(str(instruction_file))

    assert "Missing required field 'name'" in exc_info.value.message
    assert exc_info.value.code == "instruction_missing_field"


def test_load_instruction_missing_version(tmp_path: Path):
    """Test loading instruction file with missing 'version' field."""
    instruction_file = tmp_path / "missing-version.md"
    instruction_file.write_text("""---
name: test
description: Missing version field
---

<objective>Test</objective>
""")

    with pytest.raises(InstructionValidationError) as exc_info:
        load_instruction(str(instruction_file))

    assert "Missing required field 'version'" in exc_info.value.message


def test_load_instruction_empty_body(tmp_path: Path):
    """Test loading instruction file with empty body."""
    instruction_file = tmp_path / "empty-body.md"
    instruction_file.write_text("""---
name: test
description: Empty body
version: 1.0.0
---

""")

    with pytest.raises(InstructionValidationError) as exc_info:
        load_instruction(str(instruction_file))

    assert "Instruction body is empty" in exc_info.value.message
    assert exc_info.value.code == "instruction_empty_body"


def test_load_instruction_malformed_xml(tmp_path: Path):
    """Test loading instruction file with malformed XML."""
    instruction_file = tmp_path / "malformed-xml.md"
    instruction_file.write_text("""---
name: test
description: Malformed XML
version: 1.0.0
---

<objective>
Unclosed tag
<workflow>
More content
""")

    with pytest.raises(InstructionParseError) as exc_info:
        load_instruction(str(instruction_file))

    assert "Malformed XML" in exc_info.value.message
    assert exc_info.value.code == "instruction_malformed_xml"


def test_load_instruction_file_not_found():
    """Test loading non-existent instruction file."""
    with pytest.raises(InstructionParseError) as exc_info:
        load_instruction("/nonexistent/file.md")

    assert "Instruction file not found" in exc_info.value.message
    assert exc_info.value.code == "instruction_file_not_found"


def test_load_instruction_optional_trigger(tmp_path: Path):
    """Test loading instruction without optional 'trigger' field (for main instruction)."""
    instruction_file = tmp_path / "no-trigger.md"
    instruction_file.write_text("""---
name: main-instruction
description: Main instruction without trigger
version: 1.0.0
---

<objective>Main instruction content</objective>
""")

    instruction = load_instruction(str(instruction_file))

    assert instruction.name == "main-instruction"
    assert instruction.trigger is None


def test_instruction_caching(tmp_path: Path):
    """Test instruction caching functionality."""
    # Clear cache first
    clear_instruction_cache()

    # Create instruction file
    instruction_file = tmp_path / "cached-instruction.md"
    instruction_file.write_text("""---
name: cached
description: Cached instruction
version: 1.0.0
---

<objective>Cached content</objective>
""")

    # Load first time - should cache
    instruction1 = load_instruction_cached(str(instruction_file))
    assert instruction1.name == "cached"

    # Load second time - should return from cache
    instruction2 = load_instruction_cached(str(instruction_file))
    assert instruction2.name == "cached"
    assert instruction1 is instruction2  # Same object from cache

    # Clear cache
    clear_instruction_cache()

    # Load again - should reload
    instruction3 = load_instruction_cached(str(instruction_file))
    assert instruction3.name == "cached"
    assert instruction1 is not instruction3  # Different object after cache clear


def test_validate_instruction_valid(tmp_path: Path):
    """Test validation of a valid instruction."""
    instruction_file = tmp_path / "valid-instruction.md"
    instruction_file.write_text("""---
name: valid
description: Valid instruction
version: 1.0.0
---

<objective>Valid content</objective>
""")

    instruction = load_instruction(str(instruction_file))

    # Should not raise
    validate_instruction(instruction)


def test_validate_instruction_empty_name(tmp_path: Path):
    """Test validation with empty name."""
    # Manually create InstructionFile with empty name
    instruction = InstructionFile(
        name="",
        description="Test",
        trigger=None,
        version="1.0.0",
        body="<objective>Test</objective>",
        file_path="/test/path.md"
    )

    with pytest.raises(InstructionValidationError) as exc_info:
        validate_instruction(instruction)

    assert "Instruction name is empty" in exc_info.value.message
    assert exc_info.value.code == "instruction_invalid_name"


def test_validate_instruction_empty_version(tmp_path: Path):
    """Test validation with empty version."""
    instruction = InstructionFile(
        name="test",
        description="Test",
        trigger=None,
        version="",
        body="<objective>Test</objective>",
        file_path="/test/path.md"
    )

    with pytest.raises(InstructionValidationError) as exc_info:
        validate_instruction(instruction)

    assert "Instruction version is empty" in exc_info.value.message


def test_validate_instruction_empty_body(tmp_path: Path):
    """Test validation with empty body."""
    instruction = InstructionFile(
        name="test",
        description="Test",
        trigger=None,
        version="1.0.0",
        body="",
        file_path="/test/path.md"
    )

    with pytest.raises(InstructionValidationError) as exc_info:
        validate_instruction(instruction)

    assert "Instruction body is empty" in exc_info.value.message
    assert exc_info.value.code == "instruction_empty_body"


def test_instruction_file_plain_text_body(tmp_path: Path):
    """Test that instruction files with plain text (no XML) are accepted."""
    instruction_file = tmp_path / "plain-text.md"
    instruction_file.write_text("""---
name: plain-text
description: Plain text instruction
version: 1.0.0
---

This is plain text without XML tags.
It should be accepted as valid.
""")

    instruction = load_instruction(str(instruction_file))

    assert instruction.name == "plain-text"
    assert "plain text without XML" in instruction.body


# Function loading tests

def test_load_instruction_with_functions(tmp_path: Path):
    """Test loading instruction with available_functions in frontmatter."""
    instruction_file = tmp_path / "with-functions.md"
    instruction_file.write_text("""---
name: valid-warranty
description: Valid warranty scenario
version: 2.0.0
trigger: valid-warranty
available_functions:
  - name: check_warranty
    description: Check warranty status for serial number
    parameters:
      type: object
      properties:
        serial_number:
          type: string
          description: Product serial number
      required: [serial_number]
  - name: send_email
    description: Send email to customer
    parameters:
      type: object
      properties:
        to:
          type: string
          description: Recipient email
        subject:
          type: string
          description: Email subject
        body:
          type: string
          description: Email body
      required: [to, subject, body]
---

<objective>Handle valid warranty requests</objective>
""")

    instruction = load_instruction(str(instruction_file))

    assert instruction.name == "valid-warranty"
    assert len(instruction.available_functions) == 2
    assert instruction.available_functions[0]["name"] == "check_warranty"
    assert instruction.available_functions[1]["name"] == "send_email"
    assert instruction.has_functions() is True


def test_load_instruction_no_functions(tmp_path: Path):
    """Test loading instruction without available_functions."""
    instruction_file = tmp_path / "no-functions.md"
    instruction_file.write_text("""---
name: main
description: Main instruction
version: 1.0.0
---

<objective>Main orchestration</objective>
""")

    instruction = load_instruction(str(instruction_file))

    assert instruction.available_functions == []
    assert instruction.has_functions() is False


def test_load_instruction_empty_functions_list(tmp_path: Path):
    """Test loading instruction with empty available_functions list."""
    instruction_file = tmp_path / "empty-functions.md"
    instruction_file.write_text("""---
name: missing-info
description: Missing info scenario
version: 1.0.0
available_functions: []
---

<objective>Request missing info</objective>
""")

    instruction = load_instruction(str(instruction_file))

    assert instruction.available_functions == []
    assert instruction.has_functions() is False


def test_get_available_functions(tmp_path: Path):
    """Test get_available_functions returns FunctionDefinition objects."""
    instruction_file = tmp_path / "get-functions.md"
    instruction_file.write_text("""---
name: test-scenario
description: Test scenario
version: 1.0.0
available_functions:
  - name: check_warranty
    description: Check warranty status
    parameters:
      type: object
      properties:
        serial_number:
          type: string
      required: [serial_number]
---

<objective>Test</objective>
""")

    instruction = load_instruction(str(instruction_file))
    functions = instruction.get_available_functions()

    assert len(functions) == 1
    assert functions[0].name == "check_warranty"
    assert functions[0].description == "Check warranty status"
    assert functions[0].parameters["type"] == "object"
    assert "serial_number" in functions[0].parameters["properties"]

    # Test to_gemini_tool method
    gemini_tool = functions[0].to_gemini_tool()
    assert gemini_tool["name"] == "check_warranty"


def test_load_instruction_function_missing_name(tmp_path: Path):
    """Test loading instruction with function missing 'name'."""
    instruction_file = tmp_path / "missing-func-name.md"
    instruction_file.write_text("""---
name: test
description: Test
version: 1.0.0
available_functions:
  - description: Missing name field
    parameters:
      type: object
---

<objective>Test</objective>
""")

    with pytest.raises(InstructionValidationError) as exc_info:
        load_instruction(str(instruction_file))

    assert "missing 'name'" in exc_info.value.message.lower()
    assert exc_info.value.code == "instruction_function_missing_name"


def test_load_instruction_function_missing_description(tmp_path: Path):
    """Test loading instruction with function missing 'description'."""
    instruction_file = tmp_path / "missing-func-desc.md"
    instruction_file.write_text("""---
name: test
description: Test
version: 1.0.0
available_functions:
  - name: check_warranty
    parameters:
      type: object
---

<objective>Test</objective>
""")

    with pytest.raises(InstructionValidationError) as exc_info:
        load_instruction(str(instruction_file))

    assert "missing 'description'" in exc_info.value.message.lower()
    assert exc_info.value.code == "instruction_function_missing_description"


def test_load_instruction_function_default_parameters(tmp_path: Path):
    """Test function with no parameters gets default empty object."""
    instruction_file = tmp_path / "default-params.md"
    instruction_file.write_text("""---
name: test
description: Test
version: 1.0.0
available_functions:
  - name: get_status
    description: Get current status
---

<objective>Test</objective>
""")

    instruction = load_instruction(str(instruction_file))

    assert len(instruction.available_functions) == 1
    func = instruction.available_functions[0]
    assert func["name"] == "get_status"
    assert func["parameters"]["type"] == "object"
    assert func["parameters"]["properties"] == {}


def test_load_instruction_function_with_enum(tmp_path: Path):
    """Test function parameter with enum values."""
    instruction_file = tmp_path / "enum-params.md"
    instruction_file.write_text("""---
name: test
description: Test
version: 1.0.0
available_functions:
  - name: create_ticket
    description: Create support ticket
    parameters:
      type: object
      properties:
        priority:
          type: string
          description: Ticket priority
          enum: [low, normal, high, urgent]
      required: [priority]
---

<objective>Test</objective>
""")

    instruction = load_instruction(str(instruction_file))
    functions = instruction.get_available_functions()

    assert len(functions) == 1
    priority_param = functions[0].parameters["properties"]["priority"]
    assert priority_param["enum"] == ["low", "normal", "high", "urgent"]


def test_load_step_instruction():
    """Test loading step instruction from instructions/steps/ directory."""
    from pathlib import Path

    # Load step 01 (extract-serial)
    instruction = load_step_instruction("01-extract-serial")

    assert instruction.name == "step-01-extract-serial"
    assert instruction.description == "Step 1 - Extract serial number from customer email"
    assert instruction.version == "1.0.0"
    assert "NEXT_STEP" in instruction.body
    assert "Serial Number" in instruction.body


def test_load_step_instruction_with_cache():
    """Test step instruction caching works."""
    clear_instruction_cache()

    # First load
    instruction1 = load_step_instruction("01-extract-serial")

    # Second load (should use cache)
    instruction2 = load_step_instruction("01-extract-serial")

    # Should be same object from cache
    assert instruction1.file_path == instruction2.file_path
    assert instruction1.name == instruction2.name

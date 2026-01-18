"""Unit tests for instruction loader."""

import pytest
from pathlib import Path

from guarantee_email_agent.instructions.loader import (
    InstructionFile,
    load_instruction,
    load_instruction_cached,
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

"""Tests for eval loader."""

import pytest
from pathlib import Path
from guarantee_email_agent.eval.loader import EvalLoader
from guarantee_email_agent.eval.models import EvalTestCase
from guarantee_email_agent.utils.errors import EvalError


@pytest.fixture
def valid_yaml_content():
    """Return valid YAML content for test case."""
    return """scenario_id: test_001
description: "Test scenario"
category: test-category
created: "2026-01-18"

input:
  email:
    subject: "Test subject"
    body: "Test body with SN12345"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

  mock_responses:
    warranty_api:
      status: "valid"
      expiration_date: "2025-12-31"

expected_output:
  email_sent: true
  response_body_contains:
    - "warranty is valid"
    - "2025-12-31"
  response_body_excludes:
    - "expired"
  ticket_created: true
  ticket_fields:
    serial_number: "SN12345"
    priority: "normal"
  scenario_instruction_used: "valid-warranty"
  processing_time_ms: 60000
"""


@pytest.fixture
def loader():
    """Create EvalLoader instance."""
    return EvalLoader()


def test_load_valid_yaml(tmp_path, loader, valid_yaml_content):
    """Test loading valid YAML test case."""
    # Create temp YAML file
    yaml_file = tmp_path / "test_001.yaml"
    yaml_file.write_text(valid_yaml_content)

    # Load test case
    test_case = loader.load_eval_test_case(str(yaml_file))

    # Verify loaded data
    assert isinstance(test_case, EvalTestCase)
    assert test_case.scenario_id == "test_001"
    assert test_case.description == "Test scenario"
    assert test_case.category == "test-category"
    assert test_case.created == "2026-01-18"

    # Verify input section
    assert test_case.input.email.subject == "Test subject"
    assert test_case.input.email.body == "Test body with SN12345"
    assert test_case.input.email.from_address == "test@example.com"
    assert test_case.input.email.received == "2026-01-18T10:00:00Z"
    assert test_case.input.mock_responses["warranty_api"]["status"] == "valid"

    # Verify expected output
    assert test_case.expected_output.email_sent is True
    assert "warranty is valid" in test_case.expected_output.response_body_contains
    assert "expired" in test_case.expected_output.response_body_excludes
    assert test_case.expected_output.ticket_created is True
    assert test_case.expected_output.ticket_fields["serial_number"] == "SN12345"
    assert test_case.expected_output.scenario_instruction_used == "valid-warranty"
    assert test_case.expected_output.processing_time_ms == 60000


def test_load_yaml_missing_file(loader):
    """Test loading non-existent file raises EvalError."""
    with pytest.raises(EvalError) as exc_info:
        loader.load_eval_test_case("nonexistent.yaml")

    assert exc_info.value.code == "eval_file_not_found"
    assert "nonexistent.yaml" in exc_info.value.message


def test_load_yaml_invalid_syntax(tmp_path, loader):
    """Test loading malformed YAML raises EvalError."""
    yaml_file = tmp_path / "invalid.yaml"
    yaml_file.write_text("{ invalid yaml: [unclosed")

    with pytest.raises(EvalError) as exc_info:
        loader.load_eval_test_case(str(yaml_file))

    assert exc_info.value.code == "eval_yaml_invalid"


def test_load_yaml_missing_required_field(tmp_path, loader):
    """Test loading YAML with missing required field raises EvalError."""
    yaml_content = """scenario_id: test_002
description: "Missing category field"
created: 2026-01-18

input:
  email:
    subject: "Test"
    body: "Test"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

expected_output:
  email_sent: true
  ticket_created: false
  scenario_instruction_used: "test"
"""

    yaml_file = tmp_path / "missing_field.yaml"
    yaml_file.write_text(yaml_content)

    with pytest.raises(EvalError) as exc_info:
        loader.load_eval_test_case(str(yaml_file))

    assert exc_info.value.code == "eval_missing_field"
    assert "category" in str(exc_info.value.details.get("field", ""))


def test_load_yaml_missing_email_field(tmp_path, loader):
    """Test loading YAML with missing email field raises EvalError."""
    yaml_content = """scenario_id: test_003
description: "Missing email subject"
category: test
created: 2026-01-18

input:
  email:
    body: "Test"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

expected_output:
  email_sent: true
  ticket_created: false
  scenario_instruction_used: "test"
"""

    yaml_file = tmp_path / "missing_email.yaml"
    yaml_file.write_text(yaml_content)

    with pytest.raises(EvalError) as exc_info:
        loader.load_eval_test_case(str(yaml_file))

    assert exc_info.value.code == "eval_missing_field"
    assert "input.email.subject" in str(exc_info.value.details.get("field", ""))


def test_load_yaml_missing_expected_output_field(tmp_path, loader):
    """Test loading YAML with missing expected_output field raises EvalError."""
    yaml_content = """scenario_id: test_004
description: "Missing scenario_instruction_used"
category: test
created: 2026-01-18

input:
  email:
    subject: "Test"
    body: "Test"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

expected_output:
  email_sent: true
  ticket_created: false
"""

    yaml_file = tmp_path / "missing_output.yaml"
    yaml_file.write_text(yaml_content)

    with pytest.raises(EvalError) as exc_info:
        loader.load_eval_test_case(str(yaml_file))

    assert exc_info.value.code == "eval_missing_field"
    assert "scenario_instruction_used" in str(exc_info.value.details.get("field", ""))


def test_load_yaml_optional_fields_default(tmp_path, loader):
    """Test that optional fields get default values."""
    yaml_content = """scenario_id: test_005
description: "Test optional fields"
category: test
created: 2026-01-18

input:
  email:
    subject: "Test"
    body: "Test"
    from: "test@example.com"
    received: "2026-01-18T10:00:00Z"

expected_output:
  email_sent: true
  ticket_created: false
  scenario_instruction_used: "test"
"""

    yaml_file = tmp_path / "optional_fields.yaml"
    yaml_file.write_text(yaml_content)

    test_case = loader.load_eval_test_case(str(yaml_file))

    # Check defaults
    assert test_case.input.mock_responses == {}
    assert test_case.expected_output.response_body_contains == []
    assert test_case.expected_output.response_body_excludes == []
    assert test_case.expected_output.ticket_fields is None
    assert test_case.expected_output.processing_time_ms == 60000  # Default


def test_discover_test_cases_empty_directory(tmp_path, loader):
    """Test discovering test cases in empty directory."""
    test_cases = loader.discover_test_cases(str(tmp_path))

    assert test_cases == []


def test_discover_test_cases_nonexistent_directory(loader, caplog):
    """Test discovering test cases in nonexistent directory."""
    test_cases = loader.discover_test_cases("nonexistent_dir")

    assert test_cases == []
    assert "not found" in caplog.text


def test_discover_test_cases_multiple_files(tmp_path, loader, valid_yaml_content):
    """Test discovering multiple test case files."""
    # Create multiple valid YAML files
    (tmp_path / "test_001.yaml").write_text(valid_yaml_content)

    yaml_content_2 = valid_yaml_content.replace("test_001", "test_002").replace(
        "Test scenario", "Second test"
    )
    (tmp_path / "test_002.yaml").write_text(yaml_content_2)

    test_cases = loader.discover_test_cases(str(tmp_path))

    assert len(test_cases) == 2
    assert test_cases[0].scenario_id == "test_001"
    assert test_cases[1].scenario_id == "test_002"


def test_discover_test_cases_skip_invalid(tmp_path, loader, valid_yaml_content, caplog):
    """Test that discovery continues after encountering invalid file."""
    # Create valid file
    (tmp_path / "valid_001.yaml").write_text(valid_yaml_content)

    # Create invalid file
    (tmp_path / "invalid_002.yaml").write_text("{ invalid yaml")

    # Create another valid file
    yaml_content_2 = valid_yaml_content.replace("test_001", "valid_003")
    (tmp_path / "valid_003.yaml").write_text(yaml_content_2)

    test_cases = loader.discover_test_cases(str(tmp_path))

    # Should load 2 valid cases, skip 1 invalid
    assert len(test_cases) == 2
    assert "Failed to load invalid_002.yaml" in caplog.text


def test_discover_test_cases_sorted_order(tmp_path, loader, valid_yaml_content):
    """Test that discovered test cases are sorted by filename."""
    # Create files in reverse order
    for i in [3, 1, 2]:
        content = valid_yaml_content.replace("test_001", f"test_{i:03d}")
        (tmp_path / f"test_{i:03d}.yaml").write_text(content)

    test_cases = loader.discover_test_cases(str(tmp_path))

    # Should be sorted
    assert len(test_cases) == 3
    assert test_cases[0].scenario_id == "test_001"
    assert test_cases[1].scenario_id == "test_002"
    assert test_cases[2].scenario_id == "test_003"

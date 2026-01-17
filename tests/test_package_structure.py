"""Tests for package structure and integrity."""

import importlib
from pathlib import Path


def test_all_subdirectories_have_init():
    """Verify all package subdirectories have __init__.py files."""
    src_path = Path("src/guarantee_email_agent")

    expected_subdirs = [
        "config",
        "email",
        "instructions",
        "integrations",
        "llm",
        "eval",
        "utils",
    ]

    for subdir in expected_subdirs:
        init_file = src_path / subdir / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in {subdir}/"


def test_package_has_version():
    """Verify package __init__.py exports __version__."""
    import guarantee_email_agent

    assert hasattr(guarantee_email_agent, "__version__"), "Package missing __version__ export"
    assert isinstance(guarantee_email_agent.__version__, str), "__version__ must be a string"
    assert guarantee_email_agent.__version__ == "0.1.0", f"Expected version 0.1.0, got {guarantee_email_agent.__version__}"


def test_cli_module_importable():
    """Verify CLI module can be imported."""
    from guarantee_email_agent import cli

    assert hasattr(cli, "app"), "cli module missing Typer app"


def test_main_module_importable():
    """Verify __main__ module can be imported."""
    spec = importlib.util.find_spec("guarantee_email_agent.__main__")
    assert spec is not None, "__main__.py not found in package"


def test_project_structure_directories_exist():
    """Verify all required project directories exist."""
    required_dirs = [
        "src/guarantee_email_agent",
        "tests",
        "instructions/scenarios",
        "evals/scenarios",
        "mcp_servers/warranty_mcp_server",
        "mcp_servers/ticketing_mcp_server",
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        assert path.exists(), f"Missing required directory: {dir_path}"
        assert path.is_dir(), f"Path exists but is not a directory: {dir_path}"


def test_python_version_file_exists():
    """Verify .python-version file exists and specifies correct version."""
    version_file = Path(".python-version")
    assert version_file.exists(), "Missing .python-version file"

    content = version_file.read_text().strip()
    assert content == "3.10", f"Expected Python 3.10, got {content}"

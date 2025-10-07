"""
Unit tests for the dependency verification script.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
sys.path.insert(0, "scripts")
from verify_dependencies import DEPENDENCIES, verify_imports


def test_dependencies_list_not_empty():
    """Verify that the DEPENDENCIES list is populated."""
    assert len(DEPENDENCIES) > 0, "DEPENDENCIES list should not be empty"


def test_dependencies_list_structure():
    """Verify that each dependency entry has the correct structure."""
    for dep in DEPENDENCIES:
        assert len(dep) == 2, f"Dependency {dep} should have exactly 2 elements"
        module_name, display_name = dep
        assert isinstance(module_name, str), (
            f"Module name should be string: {module_name}"
        )
        assert isinstance(display_name, str), (
            f"Display name should be string: {display_name}"
        )


@patch("verify_dependencies.import_module")
@patch("builtins.print")
def test_verify_imports_all_succeed(mock_print, mock_import):
    """Test verify_imports when all imports succeed."""
    mock_import.return_value = MagicMock()

    with pytest.raises(SystemExit) as exc_info:
        verify_imports()

    assert exc_info.value.code == 0, "Should exit with code 0 on success"
    # Verify success message was printed
    success_calls = [
        call for call in mock_print.call_args_list if "[SUCCESS]" in str(call)
    ]
    assert len(success_calls) > 0, "Should print success message"


@patch("verify_dependencies.import_module")
@patch("builtins.print")
def test_verify_imports_some_fail(mock_print, mock_import):
    """Test verify_imports when some imports fail."""

    def side_effect(module_name):
        if module_name == "nonexistent_module":
            raise ImportError(f"No module named '{module_name}'")
        return MagicMock()

    mock_import.side_effect = side_effect

    # Temporarily add a failing dependency
    original_deps = DEPENDENCIES.copy()
    DEPENDENCIES.append(("nonexistent_module", "Nonexistent Module"))

    try:
        with pytest.raises(SystemExit) as exc_info:
            verify_imports()

        assert exc_info.value.code == 1, "Should exit with code 1 on failure"
        # Verify error message was printed
        error_calls = [
            call for call in mock_print.call_args_list if "[ERROR]" in str(call)
        ]
        assert len(error_calls) > 0, "Should print error message"
    finally:
        # Restore original dependencies
        DEPENDENCIES.clear()
        DEPENDENCIES.extend(original_deps)


@patch("verify_dependencies.import_module")
@patch("builtins.print")
def test_verify_imports_prints_progress(mock_print, mock_import):
    """Test that verify_imports prints progress for each dependency."""
    mock_import.return_value = MagicMock()

    with pytest.raises(SystemExit):
        verify_imports()

    # Should print at least one status line per dependency
    ok_calls = [call for call in mock_print.call_args_list if "[OK]" in str(call)]
    assert len(ok_calls) == len(DEPENDENCIES), "Should print OK for each dependency"

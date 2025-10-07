"""
Example unit test template for Lab Finder project.

This file demonstrates testing patterns used in this project:
- AAA (Arrange-Act-Assert) pattern
- Async test examples with pytest-asyncio
- Mocking with pytest-mock
- Type hints for test functions
"""

import pytest
from typing import Any


# ============================================================================
# Basic Unit Test Example - AAA Pattern
# ============================================================================


def example_function(input_value: int) -> int:
    """Example function to demonstrate testing."""
    return input_value * 2


def test_example_function() -> None:
    """
    Basic unit test following AAA (Arrange-Act-Assert) pattern.

    AAA Pattern:
    - Arrange: Set up test data and expected results
    - Act: Execute the function under test
    - Assert: Verify the result matches expectations
    """
    # Arrange - Set up test inputs and expected outputs
    input_value = 5
    expected_output = 10

    # Act - Execute the function being tested
    result = example_function(input_value)

    # Assert - Verify the result
    assert result == expected_output
    assert isinstance(result, int)


# ============================================================================
# Async Test Example - pytest-asyncio
# ============================================================================


async def async_function(input_value: str) -> dict[str, Any]:
    """Example async function to demonstrate async testing."""
    # Simulate async operation (e.g., API call, database query)
    return {"status": "success", "data": input_value.upper()}


@pytest.mark.asyncio
async def test_async_function() -> None:
    """
    Async test example using pytest-asyncio.

    Use @pytest.mark.asyncio decorator for async tests.
    The function must be async (async def) and await async calls.
    """
    # Arrange
    input_value = "test"

    # Act
    result = await async_function(input_value)

    # Assert
    assert result is not None
    assert result["status"] == "success"
    assert result["data"] == "TEST"


# ============================================================================
# Mock Example - pytest-mock
# ============================================================================


def function_using_dependency(external_service: Any) -> Any:
    """Example function that depends on external service."""
    return external_service.get_data()


def test_with_mock(mocker: Any) -> None:
    """
    Mock example using pytest-mock (mocker fixture).

    Mocking is used to isolate the function under test from external dependencies.
    The 'mocker' fixture is provided by pytest-mock plugin.
    """
    # Arrange - Create a mock object and define its behavior
    mock_service = mocker.Mock()
    mock_service.get_data.return_value = "mocked data"

    # Act - Call function with mocked dependency
    result = function_using_dependency(mock_service)

    # Assert - Verify result and mock was called correctly
    assert result == "mocked data"
    mock_service.get_data.assert_called_once()


# ============================================================================
# Patching Example - mocker.patch
# ============================================================================


def test_with_patch(mocker: Any) -> None:
    """
    Patch example using mocker.patch to replace module-level functions.

    Use this when you need to mock imports or module-level functions.
    Format: 'module.path.to.function'

    Note: In this example, we're patching within the same test module.
    In real tests, you would patch the function at its import location.
    Example: mocker.patch('src.utils.validator.load_schema')
    """
    # Arrange - Patch a function at its import location
    mock_function = mocker.patch("tests.unit.test_example.example_function")
    mock_function.return_value = 99

    # Act
    result = example_function(5)

    # Assert
    assert result == 99
    mock_function.assert_called_once_with(5)


# ============================================================================
# Parametrized Test Example
# ============================================================================


@pytest.mark.parametrize(
    "input_value,expected",
    [
        (1, 2),
        (5, 10),
        (10, 20),
        (0, 0),
        (-5, -10),
    ],
)
def test_example_function_parametrized(input_value: int, expected: int) -> None:
    """
    Parametrized test example - runs the same test with different inputs.

    This reduces code duplication when testing multiple input/output combinations.
    """
    # Act
    result = example_function(input_value)

    # Assert
    assert result == expected


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def function_that_raises(value: int) -> int:
    """Example function that raises an exception."""
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value


def test_exception_handling() -> None:
    """
    Test that a function raises the expected exception.

    Use pytest.raises context manager to verify exceptions.
    """
    # Arrange
    invalid_value = -1

    # Act & Assert - Verify the exception is raised
    with pytest.raises(ValueError, match="Value must be non-negative"):
        function_that_raises(invalid_value)


def test_edge_case_empty_input() -> None:
    """
    Test edge case with empty/None input.

    Always test edge cases: None, empty strings, empty lists, zero, etc.
    """
    # This is a placeholder - adapt to your actual function
    assert example_function(0) == 0


# ============================================================================
# Fixture Example
# ============================================================================


@pytest.fixture
def sample_data() -> dict[str, Any]:
    """
    Pytest fixture provides reusable test data.

    Fixtures are functions decorated with @pytest.fixture.
    They can be injected into tests by adding them as parameters.
    """
    return {
        "name": "Test Lab",
        "pi_name": "Dr. Smith",
        "research_areas": ["AI", "ML", "NLP"],
    }


def test_with_fixture(sample_data: dict[str, Any]) -> None:
    """
    Test using a fixture for shared test data.

    The fixture is automatically called and its return value is passed to the test.
    """
    # Arrange - sample_data is provided by the fixture

    # Act
    lab_name = sample_data["name"]

    # Assert
    assert lab_name == "Test Lab"
    assert len(sample_data["research_areas"]) == 3

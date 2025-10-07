"""
Example integration test template for Lab Finder project.

Integration tests verify interactions between components and external dependencies:
- File I/O operations
- MCP server interactions
- Web scraping
- Database operations
- Multi-component workflows

Mark integration tests with @pytest.mark.integration
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Any


# ============================================================================
# File I/O Integration Test
# ============================================================================


@pytest.mark.integration
def test_file_read_write_integration() -> None:
    """
    Integration test for file I/O operations.

    Uses temporary directory to avoid polluting the filesystem.
    Tests the full cycle: write → read → verify.
    """
    # Arrange - Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test_data.json"
        test_data = {"name": "Test Lab", "pi": "Dr. Smith"}

        # Act - Write data to file
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        # Act - Read data from file
        with open(test_file, "r") as f:
            loaded_data = json.load(f)

        # Assert - Verify data round-trip
        assert loaded_data == test_data
        assert test_file.exists()


# ============================================================================
# Async Integration Test with External Service Mock
# ============================================================================


class MockMCPServer:
    """Mock MCP server for integration testing."""

    async def search_papers(self, query: str) -> list[dict[str, Any]]:
        """Simulate paper search."""
        return [
            {"title": "Paper 1", "authors": ["Author A"], "year": 2023},
            {"title": "Paper 2", "authors": ["Author B"], "year": 2024},
        ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_integration() -> None:
    """
    Integration test for MCP server interaction.

    This tests the integration between your code and MCP server.
    In real tests, use actual MCP server or comprehensive mocks.
    """
    # Arrange - Create mock MCP server
    mcp_server = MockMCPServer()
    query = "machine learning"

    # Act - Query the server
    results = await mcp_server.search_papers(query)

    # Assert - Verify results structure and content
    assert isinstance(results, list)
    assert len(results) == 2
    assert all("title" in paper for paper in results)
    assert all("authors" in paper for paper in results)
    assert results[0]["year"] == 2023


# ============================================================================
# Multi-Component Integration Test
# ============================================================================


class DataProcessor:
    """Example component that processes data."""

    def process(self, data: list[int]) -> dict[str, Any]:
        """Process a list of numbers."""
        return {
            "count": len(data),
            "sum": sum(data),
            "average": sum(data) / len(data) if data else 0,
        }


class DataStorage:
    """Example component that stores processed data."""

    def __init__(self) -> None:
        self.storage: list[dict[str, Any]] = []

    def save(self, data: dict[str, Any]) -> None:
        """Save processed data."""
        self.storage.append(data)

    def get_all(self) -> list[dict[str, Any]]:
        """Retrieve all stored data."""
        return self.storage


@pytest.mark.integration
def test_processor_storage_integration() -> None:
    """
    Integration test for multiple components working together.

    Tests the full workflow: process data → store → retrieve → verify.
    """
    # Arrange - Set up components
    processor = DataProcessor()
    storage = DataStorage()
    raw_data = [10, 20, 30, 40, 50]

    # Act - Process data
    processed = processor.process(raw_data)

    # Act - Store processed data
    storage.save(processed)

    # Act - Retrieve stored data
    retrieved = storage.get_all()

    # Assert - Verify end-to-end workflow
    assert len(retrieved) == 1
    assert retrieved[0]["count"] == 5
    assert retrieved[0]["sum"] == 150
    assert retrieved[0]["average"] == 30


# ============================================================================
# Checkpoint/Resume Integration Test
# ============================================================================


@pytest.mark.integration
def test_checkpoint_restore_integration() -> None:
    """
    Integration test for checkpoint save/restore functionality.

    Tests JSONL checkpoint pattern used throughout the application.
    """
    # Arrange - Create temporary checkpoint file
    with tempfile.TemporaryDirectory() as temp_dir:
        checkpoint_file = Path(temp_dir) / "checkpoint.jsonl"

        # Test data - simulate batch checkpoints
        batch_1 = {"batch_id": 1, "data": ["item1", "item2"]}
        batch_2 = {"batch_id": 2, "data": ["item3", "item4"]}

        # Act - Save checkpoints (JSONL format)
        with open(checkpoint_file, "w") as f:
            f.write(json.dumps(batch_1) + "\n")
            f.write(json.dumps(batch_2) + "\n")

        # Act - Load checkpoints
        loaded_batches = []
        with open(checkpoint_file, "r") as f:
            for line in f:
                loaded_batches.append(json.loads(line.strip()))

        # Assert - Verify checkpoint restore
        assert len(loaded_batches) == 2
        assert loaded_batches[0]["batch_id"] == 1
        assert loaded_batches[1]["batch_id"] == 2
        assert loaded_batches[0]["data"] == ["item1", "item2"]


# ============================================================================
# Error Recovery Integration Test
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_recovery_integration() -> None:
    """
    Integration test for error handling and recovery.

    Tests graceful degradation when external dependencies fail.
    """

    # Arrange - Create a service that might fail
    class UnreliableService:
        def __init__(self) -> None:
            self.call_count = 0

        async def fetch_data(self) -> dict[str, str]:
            """Fails on first call, succeeds on retry."""
            self.call_count += 1
            if self.call_count == 1:
                raise ConnectionError("Service unavailable")
            return {"status": "success"}

    service = UnreliableService()

    # Act - Try with error handling
    try:
        await service.fetch_data()
        first_call_succeeded = True
    except ConnectionError:
        first_call_succeeded = False

    # Act - Retry after failure
    retry_result = await service.fetch_data()

    # Assert - Verify error recovery behavior
    assert first_call_succeeded is False
    assert retry_result["status"] == "success"
    assert service.call_count == 2


# ============================================================================
# Configuration Validation Integration Test
# ============================================================================


@pytest.mark.integration
def test_config_loading_integration() -> None:
    """
    Integration test for configuration loading and validation.

    Tests loading JSON config from file and validating structure.
    """
    # Arrange - Create temporary config file
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = Path(temp_dir) / "config.json"
        config_data = {
            "university": "Test University",
            "department": "Computer Science",
            "research_interests": ["AI", "ML"],
        }

        # Act - Write config
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Act - Load and validate config
        with open(config_file, "r") as f:
            loaded_config = json.load(f)

        # Assert - Verify config structure
        assert "university" in loaded_config
        assert "department" in loaded_config
        assert isinstance(loaded_config["research_interests"], list)
        assert len(loaded_config["research_interests"]) == 2


# ============================================================================
# Fixture for Integration Tests
# ============================================================================


@pytest.fixture
def temp_workspace() -> Any:
    """
    Fixture providing a temporary workspace for integration tests.

    Automatically cleans up after the test completes.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        # Create common subdirectories
        (workspace / "checkpoints").mkdir()
        (workspace / "output").mkdir()
        yield workspace
        # Cleanup happens automatically when context exits


@pytest.mark.integration
def test_with_workspace_fixture(temp_workspace: Path) -> None:
    """
    Integration test using the workspace fixture.

    Demonstrates using fixtures in integration tests.
    """
    # Arrange - Workspace is provided by fixture
    checkpoint_dir = temp_workspace / "checkpoints"
    test_file = checkpoint_dir / "test.jsonl"

    # Act - Write test data
    with open(test_file, "w") as f:
        f.write('{"test": "data"}\n')

    # Assert - Verify file was created
    assert test_file.exists()
    assert checkpoint_dir.exists()

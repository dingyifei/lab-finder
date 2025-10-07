"""
Unit tests for checkpoint_manager module.
"""

import json
import pytest
from pydantic import BaseModel
from src.utils.checkpoint_manager import CheckpointManager


class SampleModel(BaseModel):
    """Sample Pydantic model for testing."""

    id: str
    name: str
    value: int


class TestCheckpointManager:
    """Test cases for CheckpointManager class."""

    def test_initialization_creates_directory(self, tmp_path):
        """Test that CheckpointManager creates checkpoint directory."""
        # Arrange
        checkpoint_dir = tmp_path / "checkpoints"

        # Act
        CheckpointManager(checkpoint_dir=str(checkpoint_dir))

        # Assert
        assert checkpoint_dir.exists()
        assert checkpoint_dir.is_dir()

    def test_save_batch_creates_jsonl_file(self, tmp_path):
        """Test that save_batch creates JSONL file with correct data."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))
        data = [
            SampleModel(id="1", name="Alice", value=100),
            SampleModel(id="2", name="Bob", value=200),
        ]

        # Act
        manager.save_batch(phase="test-phase", batch_id=1, data=data)

        # Assert
        checkpoint_file = tmp_path / "test-phase-batch-1.jsonl"
        assert checkpoint_file.exists()

        # Verify JSONL content
        with open(checkpoint_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2

            record1 = json.loads(lines[0])
            assert record1["id"] == "1"
            assert record1["name"] == "Alice"
            assert record1["value"] == 100

    def test_load_batches_aggregates_multiple_files(self, tmp_path):
        """Test that load_batches aggregates records from multiple batch files."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        batch1 = [SampleModel(id="1", name="Alice", value=100)]
        batch2 = [SampleModel(id="2", name="Bob", value=200)]

        manager.save_batch(phase="test-phase", batch_id=1, data=batch1)
        manager.save_batch(phase="test-phase", batch_id=2, data=batch2)

        # Act
        records = manager.load_batches(phase="test-phase")

        # Assert
        assert len(records) == 2
        assert any(r["id"] == "1" and r["name"] == "Alice" for r in records)
        assert any(r["id"] == "2" and r["name"] == "Bob" for r in records)

    def test_load_batches_deduplicates_by_id(self, tmp_path):
        """Test that load_batches deduplicates records by ID (later overrides earlier)."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        batch1 = [SampleModel(id="1", name="Alice", value=100)]
        batch2 = [SampleModel(id="1", name="Alice Updated", value=150)]

        manager.save_batch(phase="test-phase", batch_id=1, data=batch1)
        manager.save_batch(phase="test-phase", batch_id=2, data=batch2)

        # Act
        records = manager.load_batches(phase="test-phase")

        # Assert
        assert len(records) == 1
        assert records[0]["id"] == "1"
        assert records[0]["name"] == "Alice Updated"
        assert records[0]["value"] == 150

    def test_load_batches_returns_empty_for_no_batches(self, tmp_path):
        """Test that load_batches returns empty list when no batches exist."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Act
        records = manager.load_batches(phase="nonexistent-phase")

        # Assert
        assert records == []

    def test_get_resume_point_returns_zero_for_no_batches(self, tmp_path):
        """Test that get_resume_point returns 0 when no batches exist."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Act
        resume_point = manager.get_resume_point(phase="test-phase")

        # Assert
        assert resume_point == 0

    def test_get_resume_point_returns_next_batch_number(self, tmp_path):
        """Test that get_resume_point returns next batch number when batches are sequential."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        batch0 = [SampleModel(id="1", name="Alice", value=100)]
        batch1 = [SampleModel(id="2", name="Bob", value=200)]
        batch2 = [SampleModel(id="3", name="Charlie", value=300)]
        batch3 = [SampleModel(id="4", name="David", value=400)]

        manager.save_batch(phase="test-phase", batch_id=0, data=batch0)
        manager.save_batch(phase="test-phase", batch_id=1, data=batch1)
        manager.save_batch(phase="test-phase", batch_id=2, data=batch2)
        manager.save_batch(phase="test-phase", batch_id=3, data=batch3)

        # Act
        resume_point = manager.get_resume_point(phase="test-phase")

        # Assert
        assert resume_point == 4

    def test_get_resume_point_identifies_missing_batch(self, tmp_path):
        """Test that get_resume_point identifies first missing batch in sequence."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        batch0 = [SampleModel(id="1", name="Alice", value=100)]
        batch2 = [SampleModel(id="3", name="Charlie", value=300)]

        manager.save_batch(phase="test-phase", batch_id=0, data=batch0)
        manager.save_batch(phase="test-phase", batch_id=2, data=batch2)

        # Act
        resume_point = manager.get_resume_point(phase="test-phase")

        # Assert
        assert resume_point == 1

    def test_mark_phase_complete_creates_marker(self, tmp_path):
        """Test that mark_phase_complete creates completion marker."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Act
        manager.mark_phase_complete(phase="test-phase")

        # Assert
        marker_file = tmp_path / "_phase_completion_markers.json"
        assert marker_file.exists()

        with open(marker_file, "r") as f:
            markers = json.load(f)
            assert markers["test-phase"] is True

    def test_mark_phase_complete_updates_existing_markers(self, tmp_path):
        """Test that mark_phase_complete updates existing markers file."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))
        manager.mark_phase_complete(phase="phase-1")

        # Act
        manager.mark_phase_complete(phase="phase-2")

        # Assert
        marker_file = tmp_path / "_phase_completion_markers.json"
        with open(marker_file, "r") as f:
            markers = json.load(f)
            assert markers["phase-1"] is True
            assert markers["phase-2"] is True

    def test_is_phase_complete_returns_true_for_completed_phase(self, tmp_path):
        """Test that is_phase_complete returns True for completed phase."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))
        manager.mark_phase_complete(phase="test-phase")

        # Act
        is_complete = manager.is_phase_complete(phase="test-phase")

        # Assert
        assert is_complete is True

    def test_is_phase_complete_returns_false_for_incomplete_phase(self, tmp_path):
        """Test that is_phase_complete returns False for incomplete phase."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Act
        is_complete = manager.is_phase_complete(phase="test-phase")

        # Assert
        assert is_complete is False

    def test_save_batch_handles_empty_data(self, tmp_path):
        """Test that save_batch handles empty data list."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))

        # Act
        manager.save_batch(phase="test-phase", batch_id=1, data=[])

        # Assert
        checkpoint_file = tmp_path / "test-phase-batch-1.jsonl"
        assert checkpoint_file.exists()

        with open(checkpoint_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 0

    def test_load_batches_handles_corrupted_file(self, tmp_path):
        """Test that load_batches raises IOError for corrupted JSONL file."""
        # Arrange
        manager = CheckpointManager(checkpoint_dir=str(tmp_path))
        corrupted_file = tmp_path / "test-phase-batch-1.jsonl"

        # Write corrupted JSON
        with open(corrupted_file, "w") as f:
            f.write("{ invalid json\n")

        # Act & Assert
        with pytest.raises(IOError) as exc_info:
            manager.load_batches(phase="test-phase")

        # Verify error message mentions either corruption or failure
        assert "Corrupted" in str(exc_info.value) or "Failed to read" in str(
            exc_info.value
        )

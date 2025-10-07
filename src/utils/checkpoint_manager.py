"""
Checkpoint Manager Module

Provides utilities for saving and loading JSONL checkpoints with batch-level resumability.
All phase agents use this module for state persistence.

Example Usage:
    from src.utils.checkpoint_manager import CheckpointManager
    from pydantic import BaseModel

    # Initialize manager
    manager = CheckpointManager()

    # Save batch
    manager.save_batch(
        phase="phase-2-professors",
        batch_id=1,
        data=[professor1, professor2, ...]
    )

    # Load batches
    batches = manager.load_batches(phase="phase-2-professors")

    # Get resume point
    resume_batch_id = manager.get_resume_point(phase="phase-2-professors")

    # Mark phase complete
    manager.mark_phase_complete(phase="phase-2-professors")
"""

import json
import jsonlines
from pathlib import Path
from typing import Sequence
from pydantic import BaseModel


class CheckpointManager:
    """Manages checkpoint saving, loading, and resumability for pipeline phases."""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize CheckpointManager.

        Args:
            checkpoint_dir: Directory path for checkpoint files (default: "checkpoints")
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.completion_marker_file = (
            self.checkpoint_dir / "_phase_completion_markers.json"
        )

    def save_batch(self, phase: str, batch_id: int, data: Sequence[BaseModel]) -> None:
        """
        Save batch data to JSONL checkpoint file.

        Args:
            phase: Phase identifier (e.g., "phase-2-professors")
            batch_id: Batch number
            data: List of Pydantic models to save

        Raises:
            IOError: If checkpoint file cannot be written
        """
        checkpoint_file = self.checkpoint_dir / f"{phase}-batch-{batch_id}.jsonl"

        try:
            with jsonlines.open(checkpoint_file, mode="w") as writer:
                for item in data:
                    # Serialize Pydantic model to dict
                    writer.write(item.model_dump())
        except Exception as e:
            raise IOError(
                f"Failed to save batch {batch_id} for phase {phase}: {e}"
            ) from e

    def load_batches(self, phase: str) -> list[dict]:
        """
        Load all completed batches for a phase.

        Args:
            phase: Phase identifier (e.g., "phase-2-professors")

        Returns:
            Aggregated list of records from all batch files.
            Later batches override earlier ones if IDs collide (deduplication by 'id' field).

        Raises:
            IOError: If checkpoint files cannot be read
        """
        batch_files = sorted(self.checkpoint_dir.glob(f"{phase}-batch-*.jsonl"))
        records: dict[str, dict] = {}

        for batch_file in batch_files:
            try:
                with jsonlines.open(batch_file) as reader:
                    for record in reader:
                        # Deduplicate by ID if present
                        record_id = record.get("id", str(record))
                        records[record_id] = record
            except json.JSONDecodeError as e:
                raise IOError(f"Corrupted checkpoint file {batch_file}: {e}") from e
            except Exception as e:
                raise IOError(
                    f"Failed to read checkpoint file {batch_file}: {e}"
                ) from e

        return list(records.values())

    def get_resume_point(self, phase: str) -> int:
        """
        Identify first missing batch number for a phase (0-indexed).

        Args:
            phase: Phase identifier (e.g., "phase-2-professors")

        Returns:
            First missing batch number (0-indexed). Returns 0 if no batches exist.

        Example:
            If batches 0, 1, 2 exist, returns 3.
            If batches 0, 2 exist (1 is missing), returns 1.
            If no batches exist, returns 0.
        """
        batch_files = list(self.checkpoint_dir.glob(f"{phase}-batch-*.jsonl"))

        if not batch_files:
            return 0

        # Extract batch numbers from filenames
        batch_numbers = []
        for batch_file in batch_files:
            try:
                # Extract batch number from filename pattern: phase-batch-N.jsonl
                batch_num = int(batch_file.stem.split("-batch-")[-1])
                batch_numbers.append(batch_num)
            except (ValueError, IndexError):
                continue

        if not batch_numbers:
            return 0

        batch_numbers.sort()

        # Find first gap in sequence
        for i, batch_num in enumerate(batch_numbers):
            expected = i  # Batches are 0-indexed
            if batch_num != expected:
                return expected

        # No gaps found, return next batch number
        return max(batch_numbers) + 1

    def mark_phase_complete(self, phase: str) -> None:
        """
        Mark a phase as complete in the completion marker file.

        Args:
            phase: Phase identifier (e.g., "phase-2-professors")

        Raises:
            IOError: If completion marker file cannot be written
        """
        # Load existing markers
        markers = {}
        if self.completion_marker_file.exists():
            try:
                with open(self.completion_marker_file, "r") as f:
                    markers = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start fresh
                markers = {}

        # Add/update phase completion marker
        markers[phase] = True

        # Write markers back to file
        try:
            with open(self.completion_marker_file, "w") as f:
                json.dump(markers, f, indent=2)
        except Exception as e:
            raise IOError(
                f"Failed to write phase completion marker for {phase}: {e}"
            ) from e

    def is_phase_complete(self, phase: str) -> bool:
        """
        Check if a phase is marked as complete.

        Args:
            phase: Phase identifier (e.g., "phase-2-professors")

        Returns:
            True if phase is marked complete, False otherwise
        """
        if not self.completion_marker_file.exists():
            return False

        try:
            with open(self.completion_marker_file, "r") as f:
                markers = json.load(f)
                return markers.get(phase, False)
        except (json.JSONDecodeError, IOError):
            return False

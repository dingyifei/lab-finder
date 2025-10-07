"""
CLI Coordinator Module

Orchestrates the multi-agent pipeline with batch processing, checkpointing, and progress tracking.
Coordinates phase execution across Epic 2-8 with resumability support.
"""

import json
from pathlib import Path
from typing import TypeVar

from src.models.config import SystemParams
from src.models.department import Department
from src.utils.checkpoint_manager import CheckpointManager
from src.utils.logger import get_logger
from src.utils.progress_tracker import ProgressTracker

T = TypeVar("T")


def divide_into_batches(items: list[T], batch_size: int) -> list[list[T]]:
    """
    Divide a list of items into batches of specified size.

    Args:
        items: List of items to batch
        batch_size: Number of items per batch

    Returns:
        List of batches, where each batch is a list of items

    Raises:
        ValueError: If batch_size <= 0

    Example:
        >>> items = [1, 2, 3, 4, 5, 6, 7]
        >>> batches = divide_into_batches(items, 3)
        >>> print(batches)
        [[1, 2, 3], [4, 5, 6], [7]]
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    if not items:
        return []

    # Handle edge case: fewer items than batch size
    if len(items) <= batch_size:
        return [items]

    # Divide into batches
    batches = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batches.append(batch)

    return batches


class CLICoordinator:
    """
    CLI Coordinator for multi-agent pipeline orchestration.

    Manages phase execution with batch processing, checkpointing, and resumability.
    Coordinates Epic 2-8 agents with progress tracking and error handling.
    """

    def __init__(
        self,
        config_path: str = "config/system_params.json",
        checkpoint_dir: str = "checkpoints",
        correlation_id: str | None = None,
    ):
        """
        Initialize CLI Coordinator.

        Args:
            config_path: Path to system parameters JSON file
            checkpoint_dir: Directory for checkpoint files
            correlation_id: Correlation ID for logging (auto-generated if None)
        """
        # Load configuration
        self.config_path = Path(config_path)
        self.system_params = self._load_config()

        # Initialize utilities
        self.checkpoint_manager = CheckpointManager(checkpoint_dir=checkpoint_dir)
        self.progress_tracker = ProgressTracker()

        # Generate correlation ID if not provided
        if correlation_id is None:
            import uuid

            correlation_id = str(uuid.uuid4())

        self.correlation_id = correlation_id
        self.logger = get_logger(
            correlation_id=correlation_id,
            phase="coordinator",
            component="cli_coordinator",
        )

        self.logger.info(
            "CLI Coordinator initialized",
            config_path=str(self.config_path),
            checkpoint_dir=checkpoint_dir,
            batch_config=self.system_params.batch_config.model_dump(),
        )

    def _load_config(self) -> SystemParams:
        """
        Load and validate system parameters from config file.

        Returns:
            SystemParams: Validated configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config validation fails
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}. "
                f"Copy {self.config_path.stem}.example.json to {self.config_path.name}"
            )

        with open(self.config_path, "r") as f:
            config_data = json.load(f)

        # Validate and return
        return SystemParams(**config_data)

    def process_departments_in_batches(
        self,
        departments: list[Department],
        phase: str = "phase-1",
        start_batch: int | None = None,
    ) -> list[Department]:
        """
        Process departments in configurable batches with checkpointing and resumability.

        Args:
            departments: List of Department objects to process
            phase: Phase identifier for checkpointing (default: "phase-1")
            start_batch: Starting batch index (None = check for resume point)

        Returns:
            List of processed Department objects

        Example:
            >>> coordinator = CLICoordinator()
            >>> departments = [...]  # List of Department objects
            >>> results = coordinator.process_departments_in_batches(departments)
        """
        batch_size = self.system_params.batch_config.department_discovery_batch_size

        # Divide into batches
        batches = divide_into_batches(departments, batch_size)
        total_batches = len(batches)

        self.logger.info(
            "Divided departments into batches",
            total_departments=len(departments),
            batch_size=batch_size,
            total_batches=total_batches,
        )

        # Determine resume point
        if start_batch is None:
            start_batch = self.checkpoint_manager.get_resume_point(phase)

        if start_batch > 0:
            self.logger.info(
                f"Resuming from batch {start_batch}",
                batches_completed=start_batch,
                batches_remaining=total_batches - start_batch,
            )

        # Initialize progress tracker
        self.progress_tracker.start_phase(
            f"Phase 1: University Discovery [batch 0/{total_batches}]",
            total_items=len(departments),
        )

        # Process batches
        all_results: list[Department] = []

        # Load already completed batches
        if start_batch > 0:
            completed_batches = self.checkpoint_manager.load_batches(phase)
            for batch_data in completed_batches:
                # Convert dict to Department if needed
                if isinstance(batch_data, dict):
                    all_results.append(Department(**batch_data))
                else:
                    all_results.append(batch_data)

        for batch_id in range(start_batch, total_batches):
            batch_departments = batches[batch_id]
            batch_start_idx = batch_id * batch_size
            batch_end_idx = min(batch_start_idx + len(batch_departments), len(departments))

            self.logger.info(
                f"Processing batch {batch_id + 1} of {total_batches}",
                departments=f"{batch_start_idx + 1}-{batch_end_idx}",
                batch_size=len(batch_departments),
            )

            # Update progress tracker - overall phase progress
            self.progress_tracker.start_phase(
                f"Phase 1: University Discovery [batch {batch_id + 1}/{total_batches}]",
                total_items=len(departments),
            )

            # Update progress tracker - batch-level progress
            self.progress_tracker.update_batch(
                batch_num=batch_id + 1,
                total_batches=total_batches,
                batch_desc=f"Processing departments {batch_start_idx + 1}-{batch_end_idx} of {len(departments)}",
            )

            # Process batch (placeholder - actual agent spawning will be implemented in Epic 2)
            batch_results = self._process_department_batch(
                batch_departments, batch_id
            )

            # Save checkpoint after batch completion
            self.checkpoint_manager.save_batch(
                phase=phase, batch_id=batch_id, data=batch_results
            )

            self.logger.info(
                f"Batch {batch_id + 1} complete, checkpoint saved",
                checkpoint_file=f"{phase}-batch-{batch_id}.jsonl",
            )

            # Aggregate results
            all_results.extend(batch_results)

            # Update progress tracker with completed items
            self.progress_tracker.update(completed=len(all_results))

        # Mark phase complete
        self.checkpoint_manager.mark_phase_complete(phase)

        # Complete progress tracker
        self.progress_tracker.complete_phase()

        self.logger.info(
            f"Phase 1 complete: {len(all_results)} departments discovered in {total_batches} batches",
            total_departments=len(all_results),
            total_batches=total_batches,
        )

        return all_results

    def _process_department_batch(
        self, batch: list[Department], batch_id: int
    ) -> list[Department]:
        """
        Process a single batch of departments.

        This is a placeholder method that will be implemented with actual
        agent spawning logic in Epic 2. Currently returns the batch as-is
        for testing purposes.

        Args:
            batch: List of Department objects in this batch
            batch_id: Batch index

        Returns:
            List of processed Department objects

        TODO: Implement actual sub-agent spawning using Claude Agent SDK
        """
        self.logger.debug(
            f"Processing batch {batch_id}",
            batch_size=len(batch),
            placeholder_implementation=True,
        )

        # Placeholder: Return batch as-is
        # TODO: Spawn sub-agents for parallel processing
        # TODO: Aggregate results from sub-agents
        return batch

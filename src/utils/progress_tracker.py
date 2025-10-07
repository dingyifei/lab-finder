"""
Progress Tracker Module

Wraps rich library for consistent progress bars across all pipeline phases.
Provides unified interface for phase-level and batch-level progress tracking.

Example Usage:
    from src.utils.progress_tracker import ProgressTracker

    tracker = ProgressTracker()

    # Start phase
    tracker.start_phase("Phase 2: Professor Discovery", total_items=100)

    # Update progress
    tracker.update(completed=20)

    # Batch-level progress
    tracker.update_batch(batch_num=3, total_batches=8, batch_desc="Processing professors 21-40")

    # Complete phase
    tracker.complete_phase()
"""

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskID,
)
from rich.console import Console
from typing import Optional


class ProgressTracker:
    """Manages progress bars for pipeline phases using rich library."""

    def __init__(self) -> None:
        """Initialize ProgressTracker with rich Progress instance."""
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None
        self.phase_name: str = ""
        self.total_items: int = 0
        self.completed_items: int = 0

    def start_phase(self, phase_name: str, total_items: int) -> None:
        """
        Initialize progress bar for a new phase.

        Args:
            phase_name: Name of the phase (e.g., "Phase 2: Professor Discovery")
            total_items: Total number of items to process in this phase

        Example:
            tracker.start_phase("Phase 2: Professor Discovery", total_items=100)
            # Displays: "Phase 2: Professor Discovery [0/100]"
        """
        self.phase_name = phase_name
        self.total_items = total_items
        self.completed_items = 0

        # Create progress bar with custom columns
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=self.console,
        )

        # Start progress display
        self.progress.start()

        # Add task
        self.task_id = self.progress.add_task(
            description=f"{phase_name}", total=total_items
        )

    def update(self, completed: int) -> None:
        """
        Update progress bar with completed count.

        Args:
            completed: Number of items completed (absolute count, not increment)

        Example:
            tracker.update(completed=20)  # Sets progress to 20/100
        """
        if self.progress is None or self.task_id is None:
            return

        # Calculate increment from last update
        increment = completed - self.completed_items
        self.completed_items = completed

        # Update progress
        self.progress.update(self.task_id, advance=increment)

    def update_batch(
        self, batch_num: int, total_batches: int, batch_desc: str = ""
    ) -> None:
        """
        Update progress with batch-level information.

        Args:
            batch_num: Current batch number (1-indexed)
            total_batches: Total number of batches
            batch_desc: Optional description of current batch

        Example:
            tracker.update_batch(
                batch_num=3,
                total_batches=8,
                batch_desc="Processing professors 21-40"
            )
            # Displays: "Phase 2 - Batch 3/8: Processing professors 21-40"
        """
        if self.progress is None or self.task_id is None:
            return

        description = f"{self.phase_name} - Batch {batch_num}/{total_batches}"
        if batch_desc:
            description += f": {batch_desc}"

        self.progress.update(self.task_id, description=description)

    def complete_phase(self) -> None:
        """
        Mark progress bar as complete and display summary.

        Displays:
            "Phase {N} complete: {total} items processed"
        """
        if self.progress is None or self.task_id is None:
            return

        # Update to 100% if not already
        if self.completed_items < self.total_items:
            self.progress.update(self.task_id, completed=self.total_items)

        # Stop progress display
        self.progress.stop()

        # Display completion summary
        self.console.print(
            f"✓ [bold green]{self.phase_name} complete:[/bold green] "
            f"{self.total_items} items processed"
        )

        # Reset state
        self.progress = None
        self.task_id = None
        self.phase_name = ""
        self.total_items = 0
        self.completed_items = 0

    def increment(self, amount: int = 1) -> None:
        """
        Increment progress by a relative amount.

        Args:
            amount: Number of items to increment by (default: 1)

        Example:
            tracker.increment()  # Increments by 1
            tracker.increment(5)  # Increments by 5
        """
        if self.progress is None or self.task_id is None:
            return

        self.completed_items += amount
        self.progress.update(self.task_id, advance=amount)

    def set_description(self, description: str) -> None:
        """
        Update the progress bar description.

        Args:
            description: New description text

        Example:
            tracker.set_description("Phase 2: Filtering professors")
        """
        if self.progress is None or self.task_id is None:
            return

        self.progress.update(self.task_id, description=description)

    def is_active(self) -> bool:
        """
        Check if progress tracker is currently active.

        Returns:
            True if progress tracking is active, False otherwise
        """
        return self.progress is not None and self.task_id is not None

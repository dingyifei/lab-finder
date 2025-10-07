"""
Unit tests for progress_tracker module.
"""

from unittest.mock import MagicMock, patch
from src.utils.progress_tracker import ProgressTracker


class TestProgressTracker:
    """Test cases for ProgressTracker class."""

    def test_initialization(self):
        """Test that ProgressTracker initializes correctly."""
        # Arrange & Act
        tracker = ProgressTracker()

        # Assert
        assert tracker.progress is None
        assert tracker.task_id is None
        assert tracker.phase_name == ""
        assert tracker.total_items == 0
        assert tracker.completed_items == 0

    @patch("src.utils.progress_tracker.Progress")
    def test_start_phase_creates_progress_bar(self, mock_progress_class):
        """Test that start_phase creates progress bar."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123  # TaskID

        tracker = ProgressTracker()

        # Act
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Assert
        assert tracker.phase_name == "Phase 1: Test"
        assert tracker.total_items == 100
        assert tracker.completed_items == 0
        mock_progress_instance.start.assert_called_once()
        mock_progress_instance.add_task.assert_called_once()

    @patch("src.utils.progress_tracker.Progress")
    def test_update_increments_progress(self, mock_progress_class):
        """Test that update increments progress bar."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Act
        tracker.update(completed=20)

        # Assert
        assert tracker.completed_items == 20
        mock_progress_instance.update.assert_called_with(123, advance=20)

    @patch("src.utils.progress_tracker.Progress")
    def test_update_batch_updates_description(self, mock_progress_class):
        """Test that update_batch updates progress description."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Act
        tracker.update_batch(
            batch_num=3, total_batches=8, batch_desc="Processing items 21-40"
        )

        # Assert
        expected_desc = "Phase 1: Test - Batch 3/8: Processing items 21-40"
        mock_progress_instance.update.assert_called_with(123, description=expected_desc)

    @patch("src.utils.progress_tracker.Progress")
    @patch("src.utils.progress_tracker.Console")
    def test_complete_phase_stops_progress(
        self, mock_console_class, mock_progress_class
    ):
        """Test that complete_phase stops progress bar."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        mock_console_instance = MagicMock()
        mock_console_class.return_value = mock_console_instance

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)
        tracker.update(completed=50)

        # Act
        tracker.complete_phase()

        # Assert
        mock_progress_instance.stop.assert_called_once()
        mock_console_instance.print.assert_called_once()
        assert tracker.progress is None
        assert tracker.task_id is None

    @patch("src.utils.progress_tracker.Progress")
    def test_increment_adds_to_progress(self, mock_progress_class):
        """Test that increment adds to current progress."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Act
        tracker.increment(5)

        # Assert
        assert tracker.completed_items == 5
        mock_progress_instance.update.assert_called_with(123, advance=5)

    @patch("src.utils.progress_tracker.Progress")
    def test_set_description_updates_description(self, mock_progress_class):
        """Test that set_description updates progress description."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Act
        tracker.set_description("New description")

        # Assert
        mock_progress_instance.update.assert_called_with(
            123, description="New description"
        )

    def test_is_active_returns_false_initially(self):
        """Test that is_active returns False before start_phase."""
        # Arrange
        tracker = ProgressTracker()

        # Act
        is_active = tracker.is_active()

        # Assert
        assert is_active is False

    @patch("src.utils.progress_tracker.Progress")
    def test_is_active_returns_true_after_start(self, mock_progress_class):
        """Test that is_active returns True after start_phase."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)

        # Act
        is_active = tracker.is_active()

        # Assert
        assert is_active is True

    @patch("src.utils.progress_tracker.Progress")
    @patch("src.utils.progress_tracker.Console")
    def test_is_active_returns_false_after_complete(
        self, mock_console_class, mock_progress_class
    ):
        """Test that is_active returns False after complete_phase."""
        # Arrange
        mock_progress_instance = MagicMock()
        mock_progress_class.return_value = mock_progress_instance
        mock_progress_instance.add_task.return_value = 123

        tracker = ProgressTracker()
        tracker.start_phase("Phase 1: Test", total_items=100)
        tracker.complete_phase()

        # Act
        is_active = tracker.is_active()

        # Assert
        assert is_active is False

    @patch("src.utils.progress_tracker.Progress")
    def test_update_does_nothing_when_not_active(self, mock_progress_class):
        """Test that update does nothing when progress is not active."""
        # Arrange
        tracker = ProgressTracker()

        # Act
        tracker.update(completed=20)

        # Assert
        assert tracker.completed_items == 0

    @patch("src.utils.progress_tracker.Progress")
    def test_increment_does_nothing_when_not_active(self, mock_progress_class):
        """Test that increment does nothing when progress is not active."""
        # Arrange
        tracker = ProgressTracker()

        # Act
        tracker.increment(5)

        # Assert
        assert tracker.completed_items == 0

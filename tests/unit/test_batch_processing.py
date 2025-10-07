"""
Unit tests for batch processing functionality.

Tests the divide_into_batches utility function and CLICoordinator batch processing logic.
"""

import json
import pytest

from src.coordinator import divide_into_batches, CLICoordinator
from src.models.department import Department


class TestDivideIntoBatches:
    """Test suite for divide_into_batches utility function."""

    def test_divide_normal_case(self):
        """Test normal batch division."""
        items = list(range(10))
        batches = divide_into_batches(items, 3)

        assert len(batches) == 4
        assert batches[0] == [0, 1, 2]
        assert batches[1] == [3, 4, 5]
        assert batches[2] == [6, 7, 8]
        assert batches[3] == [9]

    def test_divide_exact_division(self):
        """Test batch division with exact division."""
        items = list(range(9))
        batches = divide_into_batches(items, 3)

        assert len(batches) == 3
        assert batches[0] == [0, 1, 2]
        assert batches[1] == [3, 4, 5]
        assert batches[2] == [6, 7, 8]

    def test_divide_single_batch(self):
        """Test when items < batch_size (single batch)."""
        items = [1, 2, 3]
        batches = divide_into_batches(items, 5)

        assert len(batches) == 1
        assert batches[0] == [1, 2, 3]

    def test_divide_empty_list(self):
        """Test with empty list."""
        items = []
        batches = divide_into_batches(items, 5)

        assert batches == []

    def test_divide_batch_size_one(self):
        """Test with batch_size = 1 (sequential processing)."""
        items = [1, 2, 3]
        batches = divide_into_batches(items, 1)

        assert len(batches) == 3
        assert batches[0] == [1]
        assert batches[1] == [2]
        assert batches[2] == [3]

    def test_divide_large_batch(self):
        """Test with batch_size = 20 (high parallelism)."""
        items = list(range(50))
        batches = divide_into_batches(items, 20)

        assert len(batches) == 3
        assert len(batches[0]) == 20
        assert len(batches[1]) == 20
        assert len(batches[2]) == 10

    def test_divide_invalid_batch_size_zero(self):
        """Test that batch_size = 0 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be greater than 0"):
            divide_into_batches([1, 2, 3], 0)

    def test_divide_invalid_batch_size_negative(self):
        """Test that negative batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be greater than 0"):
            divide_into_batches([1, 2, 3], -1)

    def test_divide_with_departments(self):
        """Test with Department objects."""
        departments = [
            Department(id=str(i), name=f"Dept{i}", url=f"https://dept{i}.edu")
            for i in range(7)
        ]
        batches = divide_into_batches(departments, 3)

        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1
        assert batches[0][0].name == "Dept0"


class TestCLICoordinatorInitialization:
    """Test suite for CLICoordinator initialization."""

    def test_init_creates_default_config(self, tmp_path):
        """Test initialization with default config path."""
        # Create mock config file
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {"department_discovery_batch_size": 5},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        assert (
            coordinator.system_params.batch_config.department_discovery_batch_size == 5
        )
        assert coordinator.checkpoint_manager is not None
        assert coordinator.progress_tracker is not None
        assert coordinator.correlation_id is not None

    def test_init_missing_config_raises_error(self):
        """Test initialization with missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            CLICoordinator(config_path="nonexistent.json")

    def test_init_loads_batch_config(self, tmp_path):
        """Test that batch configuration is loaded correctly."""
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {
                "department_discovery_batch_size": 7,
                "professor_discovery_batch_size": 12,
                "publication_retrieval_batch_size": 25,
                "linkedin_matching_batch_size": 18,
            },
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        assert (
            coordinator.system_params.batch_config.department_discovery_batch_size == 7
        )
        assert (
            coordinator.system_params.batch_config.professor_discovery_batch_size == 12
        )


class TestBatchProcessing:
    """Test suite for batch processing functionality."""

    def test_process_departments_basic(self, tmp_path):
        """Test basic department batch processing."""
        # Setup
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {"department_discovery_batch_size": 3},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        departments = [
            Department(id=str(i), name=f"Dept{i}", url=f"https://dept{i}.edu")
            for i in range(7)
        ]

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        # Act
        results = coordinator.process_departments_in_batches(
            departments, phase="test-phase"
        )

        # Assert
        assert len(results) == 7
        assert all(isinstance(d, Department) for d in results)

        # Check checkpoints were created
        checkpoint_dir = tmp_path / "checkpoints"
        assert (checkpoint_dir / "test-phase-batch-0.jsonl").exists()
        assert (checkpoint_dir / "test-phase-batch-1.jsonl").exists()
        assert (checkpoint_dir / "test-phase-batch-2.jsonl").exists()

    def test_process_departments_with_resume(self, tmp_path):
        """Test resume from checkpoint functionality."""
        # Setup
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {"department_discovery_batch_size": 5},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        departments = [
            Department(id=str(i), name=f"Dept{i}", url=f"https://dept{i}.edu")
            for i in range(15)
        ]

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        # Simulate partial completion (first 2 batches done)
        first_batch = departments[0:5]
        second_batch = departments[5:10]
        coordinator.checkpoint_manager.save_batch("resume-test", 0, first_batch)
        coordinator.checkpoint_manager.save_batch("resume-test", 1, second_batch)

        # Act - get resume point
        resume_batch = coordinator.checkpoint_manager.get_resume_point("resume-test")

        # Assert
        assert resume_batch == 2  # Should resume from batch 2

        # Process from resume point
        results = coordinator.process_departments_in_batches(
            departments, phase="resume-test", start_batch=resume_batch
        )

        # Should have all 15 departments
        assert len(results) == 15

        # Batch 2 checkpoint should exist
        assert (tmp_path / "checkpoints" / "resume-test-batch-2.jsonl").exists()

    def test_process_empty_departments_list(self, tmp_path):
        """Test processing empty departments list."""
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {"department_discovery_batch_size": 5},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        results = coordinator.process_departments_in_batches([], phase="empty-test")

        assert results == []

    def test_process_single_department(self, tmp_path):
        """Test processing single department."""
        config_file = tmp_path / "system_params.json"
        config_data = {
            "batch_config": {"department_discovery_batch_size": 5},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file.write_text(json.dumps(config_data))

        departments = [Department(id="1", name="CS", url="https://cs.edu")]

        coordinator = CLICoordinator(
            config_path=str(config_file), checkpoint_dir=str(tmp_path / "checkpoints")
        )

        results = coordinator.process_departments_in_batches(
            departments, phase="single-test"
        )

        assert len(results) == 1
        assert results[0].name == "CS"

    def test_batch_size_configurations(self, tmp_path):
        """Test different batch size configurations."""
        departments = [
            Department(id=str(i), name=f"Dept{i}", url=f"https://dept{i}.edu")
            for i in range(20)
        ]

        # Test batch_size = 1 (sequential)
        config_data_1 = {
            "batch_config": {"department_discovery_batch_size": 1},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file_1 = tmp_path / "config1.json"
        config_file_1.write_text(json.dumps(config_data_1))

        coordinator_1 = CLICoordinator(
            config_path=str(config_file_1),
            checkpoint_dir=str(tmp_path / "checkpoints1"),
        )
        results_1 = coordinator_1.process_departments_in_batches(
            departments, phase="batch-1"
        )
        assert len(results_1) == 20

        # Test batch_size = 5 (default)
        config_data_5 = {
            "batch_config": {"department_discovery_batch_size": 5},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file_5 = tmp_path / "config5.json"
        config_file_5.write_text(json.dumps(config_data_5))

        coordinator_5 = CLICoordinator(
            config_path=str(config_file_5),
            checkpoint_dir=str(tmp_path / "checkpoints5"),
        )
        results_5 = coordinator_5.process_departments_in_batches(
            departments, phase="batch-5"
        )
        assert len(results_5) == 20

        # Test batch_size = 20 (high parallelism)
        config_data_20 = {
            "batch_config": {"department_discovery_batch_size": 20},
            "rate_limits": {"archive_org": 30, "linkedin": 10, "paper_search": 20},
            "timeouts": {"web_scraping": 30, "mcp_query": 60},
            "confidence_thresholds": {"professor_filter": 70.0, "linkedin_match": 75.0},
            "publication_years": 3,
            "log_level": "INFO",
        }
        config_file_20 = tmp_path / "config20.json"
        config_file_20.write_text(json.dumps(config_data_20))

        coordinator_20 = CLICoordinator(
            config_path=str(config_file_20),
            checkpoint_dir=str(tmp_path / "checkpoints20"),
        )
        results_20 = coordinator_20.process_departments_in_batches(
            departments, phase="batch-20"
        )
        assert len(results_20) == 20

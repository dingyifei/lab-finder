"""Unit tests for Story 2.2: Department Structure JSON Representation.

Tests cover:
- Loading departments from checkpoint
- Summary statistics calculation
- Hierarchical JSON transformation
- JSON schema validation
- Parallel processing department list
- JSON file save/load
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import jsonschema
import pytest

from src.agents.university_discovery import UniversityDiscoveryAgent
from src.models.department import Department
from src.utils.checkpoint_manager import CheckpointManager


@pytest.fixture
def sample_departments() -> list[Department]:
    """Create sample departments for testing."""
    return [
        Department(
            id="dept-001",
            name="Computer Science",
            school="School of Engineering",
            division=None,
            url="https://cs.stanford.edu",
            hierarchy_level=1,
        ),
        Department(
            id="dept-002",
            name="Electrical Engineering",
            school="School of Engineering",
            division=None,
            url="https://ee.stanford.edu",
            hierarchy_level=1,
        ),
        Department(
            id="dept-003",
            name="Biology",
            school="School of Medicine",
            division="Basic Sciences",
            url="https://bio.med.stanford.edu",
            hierarchy_level=2,
        ),
    ]


@pytest.fixture
def flat_structure_departments() -> list[Department]:
    """Create departments with flat structure (no divisions)."""
    return [
        Department(
            id="dept-101",
            name="Mathematics",
            school="College of Arts and Sciences",
            division=None,
            url="https://math.university.edu",
            hierarchy_level=1,
        ),
        Department(
            id="dept-102",
            name="Physics",
            school="College of Arts and Sciences",
            division=None,
            url="https://physics.university.edu",
            hierarchy_level=1,
        ),
    ]


@pytest.fixture
def three_level_hierarchy_departments() -> list[Department]:
    """Create departments with 3-level hierarchy."""
    return [
        Department(
            id="school-001",
            name="School of Engineering",
            school="School of Engineering",
            division=None,
            url="https://engineering.edu",
            hierarchy_level=0,
        ),
        Department(
            id="div-001",
            name="Computer Science Division",
            school="School of Engineering",
            division="Computer Science Division",
            url="https://cs.engineering.edu",
            hierarchy_level=1,
        ),
        Department(
            id="dept-001",
            name="Artificial Intelligence Lab",
            school="School of Engineering",
            division="Computer Science Division",
            url="https://ai.cs.engineering.edu",
            hierarchy_level=2,
        ),
    ]


@pytest.fixture
def mock_checkpoint_manager(sample_departments: list[Department]) -> MagicMock:
    """Create mock checkpoint manager with sample data."""
    manager = MagicMock(spec=CheckpointManager)
    # Convert departments to dict format (as stored in JSONL)
    # load_batches returns a flat list, not a dict
    dept_dicts = [dept.model_dump() for dept in sample_departments]
    manager.load_batches.return_value = dept_dicts
    return manager


@pytest.fixture
def agent_with_checkpoint(
    mock_checkpoint_manager: MagicMock,
) -> UniversityDiscoveryAgent:
    """Create agent with mocked checkpoint manager."""
    return UniversityDiscoveryAgent(
        correlation_id="test-correlation-id",
        checkpoint_manager=mock_checkpoint_manager,
    )


class TestLoadDepartmentsFromCheckpoint:
    """Tests for Task 1: Load Department Data from Checkpoint."""

    def test_load_departments_success(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test successful loading of departments from checkpoint."""
        # Act
        departments = agent_with_checkpoint.load_departments_from_checkpoint()

        # Assert
        assert len(departments) == 3
        assert all(isinstance(dept, Department) for dept in departments)
        assert departments[0].name == "Computer Science"
        assert departments[1].name == "Electrical Engineering"
        assert departments[2].name == "Biology"

    def test_load_departments_no_checkpoint_manager(self) -> None:
        """Test error when checkpoint manager not initialized."""
        # Arrange
        agent = UniversityDiscoveryAgent(
            correlation_id="test-id",
            checkpoint_manager=None,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Checkpoint manager required"):
            agent.load_departments_from_checkpoint()

    def test_load_departments_empty_checkpoint(self) -> None:
        """Test error when checkpoint file is empty."""
        # Arrange
        mock_manager = MagicMock(spec=CheckpointManager)
        mock_manager.load_batches.return_value = {}  # Empty batches
        agent = UniversityDiscoveryAgent(
            correlation_id="test-id",
            checkpoint_manager=mock_manager,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Cannot proceed without Story 2.1"):
            agent.load_departments_from_checkpoint()

    def test_load_departments_file_not_found(self) -> None:
        """Test error when checkpoint file doesn't exist."""
        # Arrange
        mock_manager = MagicMock(spec=CheckpointManager)
        mock_manager.load_batches.side_effect = FileNotFoundError(
            "Checkpoint not found"
        )
        agent = UniversityDiscoveryAgent(
            correlation_id="test-id",
            checkpoint_manager=mock_manager,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Checkpoint file not found"):
            agent.load_departments_from_checkpoint()

    def test_load_departments_deserialization_error_continues(self) -> None:
        """Test that deserialization errors are logged but processing continues."""
        # Arrange
        mock_manager = MagicMock(spec=CheckpointManager)
        # One valid department, one invalid
        mock_manager.load_batches.return_value = [
            {
                "id": "dept-001",
                "name": "Computer Science",
                "school": "Engineering",
                "division": None,
                "url": "https://cs.edu",
                "hierarchy_level": 1,
                "data_quality_flags": [],
            },
            {
                "id": "invalid",
                "name": "Missing required fields",
                # Missing required 'url' field
            },
        ]
        agent = UniversityDiscoveryAgent(
            correlation_id="test-id",
            checkpoint_manager=mock_manager,
        )

        # Act
        departments = agent.load_departments_from_checkpoint()

        # Assert - should load the valid department
        assert len(departments) == 1
        assert departments[0].name == "Computer Science"

    def test_load_departments_all_invalid(self) -> None:
        """Test error when all departments fail deserialization."""
        # Arrange
        mock_manager = MagicMock(spec=CheckpointManager)
        mock_manager.load_batches.return_value = [{"invalid": "data"}]
        agent = UniversityDiscoveryAgent(
            correlation_id="test-id",
            checkpoint_manager=mock_manager,
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to deserialize any departments"):
            agent.load_departments_from_checkpoint()


class TestCalculateDepartmentSummary:
    """Tests for Task 2: Calculate Department Count Summary."""

    def test_calculate_summary_mixed_hierarchy(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test summary calculation with mixed hierarchy levels."""
        # Act
        summary = agent_with_checkpoint.calculate_department_summary(sample_departments)

        # Assert
        assert summary["total_schools"] == 2  # Engineering, Medicine
        assert summary["total_divisions"] == 1  # Basic Sciences
        assert summary["total_departments"] == 3

    def test_calculate_summary_flat_structure(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        flat_structure_departments: list[Department],
    ) -> None:
        """Test summary calculation for flat structure (no divisions)."""
        # Act
        summary = agent_with_checkpoint.calculate_department_summary(
            flat_structure_departments
        )

        # Assert
        assert summary["total_schools"] == 1
        assert summary["total_divisions"] == 0
        assert summary["total_departments"] == 2

    def test_calculate_summary_empty_list(
        self, agent_with_checkpoint: UniversityDiscoveryAgent
    ) -> None:
        """Test summary calculation with empty department list."""
        # Act
        summary = agent_with_checkpoint.calculate_department_summary([])

        # Assert
        assert summary["total_schools"] == 0
        assert summary["total_divisions"] == 0
        assert summary["total_departments"] == 0


class TestCreateHierarchicalJson:
    """Tests for Task 3: Transform to Hierarchical JSON Structure."""

    def test_create_hierarchical_json_mixed_structure(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test hierarchical JSON creation with mixed structure."""
        # Arrange
        summary = agent_with_checkpoint.calculate_department_summary(sample_departments)

        # Act
        hierarchy = agent_with_checkpoint.create_hierarchical_json(
            sample_departments, summary
        )

        # Assert
        assert hierarchy["university"]  # Should have a university name
        assert "discovery_date" in hierarchy
        assert hierarchy["total_schools"] == 2
        assert hierarchy["total_divisions"] == 1
        assert hierarchy["total_departments"] == 3
        assert len(hierarchy["schools"]) == 2

        # Check School of Engineering (flat structure)
        eng_school = next(
            s for s in hierarchy["schools"] if s["name"] == "School of Engineering"
        )
        assert "divisions" not in eng_school  # No divisions for flat structure
        assert len(eng_school["departments"]) == 2

        # Check School of Medicine (with divisions)
        med_school = next(
            s for s in hierarchy["schools"] if s["name"] == "School of Medicine"
        )
        assert "divisions" in med_school
        assert len(med_school["divisions"]) == 1
        assert med_school["divisions"][0]["name"] == "Basic Sciences"

    def test_create_hierarchical_json_flat_structure(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        flat_structure_departments: list[Department],
    ) -> None:
        """Test hierarchical JSON for completely flat structure."""
        # Arrange
        summary = agent_with_checkpoint.calculate_department_summary(
            flat_structure_departments
        )

        # Act
        hierarchy = agent_with_checkpoint.create_hierarchical_json(
            flat_structure_departments, summary
        )

        # Assert
        assert len(hierarchy["schools"]) == 1
        school = hierarchy["schools"][0]
        assert "divisions" not in school
        assert len(school["departments"]) == 2

    def test_create_hierarchical_json_three_levels(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        three_level_hierarchy_departments: list[Department],
    ) -> None:
        """Test hierarchical JSON with 3-level hierarchy."""
        # Arrange
        summary = agent_with_checkpoint.calculate_department_summary(
            three_level_hierarchy_departments
        )

        # Act
        hierarchy = agent_with_checkpoint.create_hierarchical_json(
            three_level_hierarchy_departments, summary
        )

        # Assert
        assert len(hierarchy["schools"]) == 1
        school = hierarchy["schools"][0]
        assert "divisions" in school
        assert len(school["divisions"]) == 1
        division = school["divisions"][0]
        assert len(division["departments"]) == 1

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"university_name": "Test University"}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_university_name_from_config(
        self,
        mock_exists: MagicMock,
        mock_file: MagicMock,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test university name extraction from config file."""
        # Arrange
        summary = agent_with_checkpoint.calculate_department_summary(sample_departments)

        # Act
        hierarchy = agent_with_checkpoint.create_hierarchical_json(
            sample_departments, summary
        )

        # Assert
        assert hierarchy["university"] == "Test University"

    @patch("pathlib.Path.exists", return_value=False)
    def test_university_name_from_url(
        self,
        mock_exists: MagicMock,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test university name extraction from department URL."""
        # Arrange
        summary = agent_with_checkpoint.calculate_department_summary(sample_departments)

        # Act
        hierarchy = agent_with_checkpoint.create_hierarchical_json(
            sample_departments, summary
        )

        # Assert
        # Should extract "stanford" from https://cs.stanford.edu
        assert "stanford" in hierarchy["university"].lower()


class TestValidateHierarchicalJson:
    """Tests for Task 4: Validate JSON Schema."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "required": ["university", "discovery_date", "schools"], "properties": {"university": {"type": "string"}, "discovery_date": {"type": "string"}, "schools": {"type": "array"}}}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_json_success(
        self,
        mock_exists: MagicMock,
        mock_file: MagicMock,
        agent_with_checkpoint: UniversityDiscoveryAgent,
    ) -> None:
        """Test successful JSON validation."""
        # Arrange
        valid_json = {
            "university": "Test University",
            "discovery_date": "2025-10-07",
            "schools": [],
        }

        # Act & Assert - should not raise
        agent_with_checkpoint.validate_hierarchical_json(valid_json)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "required": ["university", "discovery_date", "schools"], "properties": {"university": {"type": "string"}, "discovery_date": {"type": "string"}, "schools": {"type": "array"}}}',
    )
    @patch("pathlib.Path.exists", return_value=True)
    def test_validate_json_missing_required_field(
        self,
        mock_exists: MagicMock,
        mock_file: MagicMock,
        agent_with_checkpoint: UniversityDiscoveryAgent,
    ) -> None:
        """Test validation failure for missing required field."""
        # Arrange
        invalid_json = {
            "university": "Test University",
            # Missing 'discovery_date' and 'schools'
        }

        # Act & Assert
        with pytest.raises(jsonschema.ValidationError):
            agent_with_checkpoint.validate_hierarchical_json(invalid_json)

    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_json_schema_file_not_found(
        self, mock_exists: MagicMock, agent_with_checkpoint: UniversityDiscoveryAgent
    ) -> None:
        """Test error when schema file doesn't exist."""
        # Arrange
        valid_json = {
            "university": "Test",
            "discovery_date": "2025-10-07",
            "schools": [],
        }

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Schema file not found"):
            agent_with_checkpoint.validate_hierarchical_json(valid_json)


class TestGetDepartmentsForParallelProcessing:
    """Tests for Task 5: Enable Parallel Async Iteration."""

    def test_get_departments_for_parallel_processing(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
    ) -> None:
        """Test getting flattened department list for parallel processing."""
        # Act
        departments = agent_with_checkpoint.get_departments_for_parallel_processing()

        # Assert
        assert len(departments) == 3
        assert all(isinstance(dept, Department) for dept in departments)
        # Verify it's a flat list (not nested)
        assert isinstance(departments, list)

    def test_get_departments_reuses_checkpoint_loader(
        self, agent_with_checkpoint: UniversityDiscoveryAgent
    ) -> None:
        """Test that method reuses checkpoint loader."""
        # Act
        departments = agent_with_checkpoint.get_departments_for_parallel_processing()

        # Assert
        agent_with_checkpoint.checkpoint_manager.load_batches.assert_called_once_with(
            "phase-1-departments"
        )
        assert len(departments) == 3


class TestSaveHierarchicalJson:
    """Tests for Task 6: Save JSON with Human-Readable Formatting."""

    def test_save_hierarchical_json_success(
        self, agent_with_checkpoint: UniversityDiscoveryAgent, tmp_path: Path
    ) -> None:
        """Test successful JSON save with human-readable formatting."""
        # Arrange
        test_json = {
            "university": "Test University",
            "discovery_date": "2025-10-07",
            "schools": [],
        }
        output_path = tmp_path / "test-structure.json"

        # Act
        saved_path = agent_with_checkpoint.save_hierarchical_json(
            test_json, output_path
        )

        # Assert
        assert saved_path == output_path
        assert output_path.exists()

        # Verify JSON is human-readable (indented)
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "  " in content  # Has indentation

        # Verify it's valid JSON
        with open(output_path, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
            assert loaded_json == test_json

    def test_save_hierarchical_json_default_path(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test save with default path."""
        # Arrange
        monkeypatch.chdir(tmp_path)  # Change to tmp directory
        test_json = {
            "university": "Test University",
            "discovery_date": "2025-10-07",
            "schools": [],
        }

        # Act
        saved_path = agent_with_checkpoint.save_hierarchical_json(test_json)

        # Assert
        assert saved_path == Path("checkpoints/phase-1-department-structure.json")
        assert saved_path.exists()

    def test_save_hierarchical_json_creates_directory(
        self, agent_with_checkpoint: UniversityDiscoveryAgent, tmp_path: Path
    ) -> None:
        """Test that parent directory is created if it doesn't exist."""
        # Arrange
        test_json = {
            "university": "Test",
            "discovery_date": "2025-10-07",
            "schools": [],
        }
        output_path = tmp_path / "new_dir" / "subdir" / "test.json"

        # Act
        saved_path = agent_with_checkpoint.save_hierarchical_json(
            test_json, output_path
        )

        # Assert
        assert saved_path.exists()
        assert saved_path.parent.exists()


class TestEndToEndWorkflow:
    """Integration tests for complete Story 2.2 workflow."""

    def test_complete_workflow(
        self,
        agent_with_checkpoint: UniversityDiscoveryAgent,
        sample_departments: list[Department],
        tmp_path: Path,
    ) -> None:
        """Test complete workflow from loading to saving."""
        # Task 1: Load departments
        departments = agent_with_checkpoint.load_departments_from_checkpoint()
        assert len(departments) == 3

        # Task 2: Calculate summary
        summary = agent_with_checkpoint.calculate_department_summary(departments)
        assert summary["total_departments"] == 3

        # Task 3: Create hierarchical JSON
        hierarchy = agent_with_checkpoint.create_hierarchical_json(departments, summary)
        assert hierarchy["university"]
        assert len(hierarchy["schools"]) == 2

        # Task 6: Save JSON
        output_path = tmp_path / "test-output.json"
        saved_path = agent_with_checkpoint.save_hierarchical_json(
            hierarchy, output_path
        )
        assert saved_path.exists()

        # Verify saved content
        with open(saved_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            assert loaded["total_departments"] == 3

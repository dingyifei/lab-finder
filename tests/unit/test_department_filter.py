"""Unit tests for department relevance filtering (Story 2.3)."""

import pytest
from unittest.mock import Mock

from src.agents.university_discovery import UniversityDiscoveryAgent
from src.models.department import Department
from src.utils.checkpoint_manager import CheckpointManager


class TestLoadUserProfile:
    """Test user profile loading functionality."""

    def test_load_profile_success(self, tmp_path, mocker):
        """Test successful profile loading with all fields."""
        # Arrange
        profile_content = """# User Research Profile

**Current Degree:** PhD in Computer Science

## Streamlined Research Interests

Machine learning and artificial intelligence, particularly deep learning and computer vision.

## Educational Background

Bachelor's in Computer Science from MIT, Master's in AI from Stanford.
"""
        profile_path = tmp_path / "user-profile.md"
        profile_path.write_text(profile_content, encoding="utf-8")

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = agent.load_user_profile(profile_path)

        # Assert
        assert "interests" in result
        assert "degree" in result
        assert "background" in result
        assert "Machine learning and artificial intelligence" in result["interests"]
        assert "PhD in Computer Science" in result["degree"]
        assert "Bachelor's in Computer Science" in result["background"]

    def test_load_profile_missing_file(self, tmp_path):
        """Test error handling when profile file doesn't exist."""
        # Arrange
        profile_path = tmp_path / "nonexistent.md"
        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Run Story 1.7"):
            agent.load_user_profile(profile_path)

    def test_load_profile_partial_fields(self, tmp_path):
        """Test profile loading with missing optional fields."""
        # Arrange
        profile_content = """# User Research Profile

## Streamlined Research Interests

Quantum computing and algorithms.
"""
        profile_path = tmp_path / "user-profile.md"
        profile_path.write_text(profile_content, encoding="utf-8")

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = agent.load_user_profile(profile_path)

        # Assert
        assert result["interests"] == "Quantum computing and algorithms."
        assert result["degree"] == ""  # Missing field
        assert result["background"] == ""  # Missing field


class TestFilterDepartments:
    """Test department filtering with LLM."""

    @pytest.mark.asyncio
    async def test_filter_departments_include_relevant(self, mocker):
        """Test that relevant departments are included."""
        # Arrange
        mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_llm.return_value = '{"decision": "include", "confidence": 95, "reasoning": "Strong match with AI research"}'

        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2
            )
        ]

        user_profile = {
            "interests": "Machine learning and AI",
            "degree": "PhD Computer Science",
            "background": "BS in CS"
        }

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = await agent.filter_departments(
            departments, user_profile, use_progress_tracker=False
        )

        # Assert
        assert len(result) == 1
        assert result[0].is_relevant is True
        assert result[0].relevance_reasoning == "Strong match with AI research"
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_departments_exclude_unrelated(self, mocker):
        """Test that unrelated departments are excluded."""
        # Arrange
        mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_llm.return_value = '{"decision": "exclude", "confidence": 90, "reasoning": "No overlap with bioengineering"}'

        departments = [
            Department(
                id="1",
                name="English Literature",
                school="Humanities",
                url="https://english.edu",
                hierarchy_level=2
            )
        ]

        user_profile = {
            "interests": "Bioengineering and tissue engineering",
            "degree": "PhD Bioengineering",
            "background": "BS in Biology"
        }

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = await agent.filter_departments(
            departments, user_profile, use_progress_tracker=False
        )

        # Assert
        assert len(result) == 1
        assert result[0].is_relevant is False
        assert "No overlap" in result[0].relevance_reasoning

    @pytest.mark.asyncio
    async def test_filter_departments_partial_overlap(self, mocker):
        """Test that departments with partial overlap are included (AC: 2)."""
        # Arrange
        mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_llm.return_value = '{"decision": "include", "confidence": 75, "reasoning": "Partial overlap with data science"}'

        departments = [
            Department(
                id="1",
                name="Statistics",
                school="Science",
                url="https://stats.edu",
                hierarchy_level=2
            )
        ]

        user_profile = {
            "interests": "Machine learning algorithms",
            "degree": "PhD Computer Science",
            "background": "BS in CS"
        }

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = await agent.filter_departments(
            departments, user_profile, use_progress_tracker=False
        )

        # Assert
        assert len(result) == 1
        assert result[0].is_relevant is True
        assert "Partial overlap" in result[0].relevance_reasoning

    @pytest.mark.asyncio
    async def test_filter_departments_empty_list(self, mocker):
        """Test handling of empty department list."""
        # Arrange
        mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')

        user_profile = {
            "interests": "Machine learning",
            "degree": "PhD CS",
            "background": "BS CS"
        }

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = await agent.filter_departments(
            [], user_profile, use_progress_tracker=False
        )

        # Assert
        assert result == []
        mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_filter_departments_llm_error_handling(self, mocker):
        """Test graceful handling of LLM errors."""
        # Arrange
        mock_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_llm.side_effect = Exception("LLM service unavailable")

        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2
            )
        ]

        user_profile = {
            "interests": "Machine learning",
            "degree": "PhD CS",
            "background": "BS CS"
        }

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        result = await agent.filter_departments(
            departments, user_profile, use_progress_tracker=False
        )

        # Assert
        assert len(result) == 1
        # Default to exclude on error
        assert result[0].is_relevant is False
        assert "Error during filtering" in result[0].relevance_reasoning


class TestEdgeCaseDetection:
    """Test edge case detection and classification (AC: 3)."""

    def test_is_edge_case_interdisciplinary(self):
        """Test detection of interdisciplinary departments."""
        # Arrange
        dept = Department(
            id="1",
            name="Computer Science & Engineering",
            school="Engineering",
            url="https://cse.edu",
            hierarchy_level=2
        )
        llm_result = {"decision": "include", "confidence": 85, "reasoning": "Test"}

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        is_edge = agent._is_edge_case(dept, llm_result)

        # Assert
        assert is_edge is True

    def test_is_edge_case_generic_department(self):
        """Test detection of generic department names."""
        # Arrange
        dept = Department(
            id="1",
            name="Graduate Studies",
            school="University",
            url="https://grad.edu",
            hierarchy_level=1
        )
        llm_result = {"decision": "include", "confidence": 70, "reasoning": "Test"}

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        is_edge = agent._is_edge_case(dept, llm_result)

        # Assert
        assert is_edge is True

    def test_is_edge_case_ambiguous_confidence(self):
        """Test detection based on ambiguous confidence score."""
        # Arrange
        dept = Department(
            id="1",
            name="Chemistry",
            school="Science",
            url="https://chem.edu",
            hierarchy_level=2
        )
        llm_result = {"decision": "include", "confidence": 50, "reasoning": "Test"}

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        is_edge = agent._is_edge_case(dept, llm_result)

        # Assert
        assert is_edge is True

    def test_is_edge_case_normal_department(self):
        """Test that normal departments are not flagged as edge cases."""
        # Arrange
        dept = Department(
            id="1",
            name="Computer Science",
            school="Engineering",
            url="https://cs.edu",
            hierarchy_level=2
        )
        llm_result = {"decision": "include", "confidence": 95, "reasoning": "Test"}

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        is_edge = agent._is_edge_case(dept, llm_result)

        # Assert
        assert is_edge is False

    def test_classify_edge_case_interdisciplinary(self):
        """Test classification of interdisciplinary edge case."""
        # Arrange
        dept = Department(
            id="1",
            name="Bioengineering & Computer Science",
            school="Engineering",
            url="https://bio-cs.edu",
            hierarchy_level=2
        )

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        classification = agent._classify_edge_case(dept)

        # Assert
        assert classification == "interdisciplinary"

    def test_classify_edge_case_generic(self):
        """Test classification of generic edge case."""
        # Arrange
        dept = Department(
            id="1",
            name="Graduate Studies",
            school="University",
            url="https://grad.edu",
            hierarchy_level=1
        )

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act
        classification = agent._classify_edge_case(dept)

        # Assert
        assert classification == "generic"


class TestSaveFilteredDepartmentsReport:
    """Test filtered departments report generation (AC: 5)."""

    def test_save_report_with_excluded_departments(self, tmp_path):
        """Test report generation with excluded departments."""
        # Arrange
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2,
                is_relevant=True,
                relevance_reasoning="Strong match"
            ),
            Department(
                id="2",
                name="English Literature",
                school="Humanities",
                url="https://english.edu",
                hierarchy_level=2,
                is_relevant=False,
                relevance_reasoning="No overlap with engineering research"
            ),
        ]

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(
            correlation_id=correlation_id,
            output_dir=output_dir
        )

        # Act
        agent.save_filtered_departments_report(departments)

        # Assert
        report_path = output_dir / "filtered-departments.md"
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")
        assert "Filtered Departments Report" in content
        assert "English Literature" in content
        assert "No overlap with engineering research" in content
        assert "Computer Science" not in content  # Should not list relevant departments

    def test_save_report_all_relevant(self, tmp_path):
        """Test report generation when all departments are relevant."""
        # Arrange
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2,
                is_relevant=True,
                relevance_reasoning="Strong match"
            ),
        ]

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(
            correlation_id=correlation_id,
            output_dir=output_dir
        )

        # Act
        agent.save_filtered_departments_report(departments)

        # Assert
        report_path = output_dir / "filtered-departments.md"
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")
        assert "Filtered Out:** 0" in content


class TestSaveRelevantDepartmentsCheckpoint:
    """Test checkpoint saving for relevant departments (AC: 6, 7)."""

    def test_save_relevant_departments_checkpoint(self, mocker, tmp_path):
        """Test saving relevant departments to checkpoint."""
        # Arrange
        checkpoints_dir = tmp_path / "checkpoints"
        checkpoints_dir.mkdir()

        mock_checkpoint_manager = Mock(spec=CheckpointManager)

        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2,
                is_relevant=True,
                relevance_reasoning="Strong match"
            ),
            Department(
                id="2",
                name="English Literature",
                school="Humanities",
                url="https://english.edu",
                hierarchy_level=2,
                is_relevant=False,
                relevance_reasoning="No overlap"
            ),
        ]

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(
            correlation_id=correlation_id,
            checkpoint_manager=mock_checkpoint_manager
        )

        # Act
        agent.save_relevant_departments_checkpoint(departments)

        # Assert
        mock_checkpoint_manager.save_batch.assert_called_once()
        call_args = mock_checkpoint_manager.save_batch.call_args

        assert call_args[1]["phase"] == "phase-1-relevant-departments"
        assert call_args[1]["batch_id"] == 0

        saved_depts = call_args[1]["data"]
        assert len(saved_depts) == 1  # Only relevant department
        assert saved_depts[0].name == "Computer Science"

    def test_save_checkpoint_no_relevant_departments(self, mocker):
        """Test checkpoint saving when no departments are relevant."""
        # Arrange
        mock_checkpoint_manager = Mock(spec=CheckpointManager)

        departments = [
            Department(
                id="1",
                name="English Literature",
                school="Humanities",
                url="https://english.edu",
                hierarchy_level=2,
                is_relevant=False,
                relevance_reasoning="No overlap"
            ),
        ]

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(
            correlation_id=correlation_id,
            checkpoint_manager=mock_checkpoint_manager
        )

        # Act
        agent.save_relevant_departments_checkpoint(departments)

        # Assert
        # Should not call save_batch when no relevant departments
        mock_checkpoint_manager.save_batch.assert_not_called()

    def test_save_checkpoint_no_checkpoint_manager(self):
        """Test error handling when checkpoint manager not initialized."""
        # Arrange
        departments = [
            Department(
                id="1",
                name="Computer Science",
                school="Engineering",
                url="https://cs.edu",
                hierarchy_level=2,
                is_relevant=True
            ),
        ]

        correlation_id = "test-123"
        agent = UniversityDiscoveryAgent(correlation_id=correlation_id)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Checkpoint manager required"):
            agent.save_relevant_departments_checkpoint(departments)


class TestLLMHelpersDepartmentRelevance:
    """Test LLM helpers for department relevance analysis."""

    @pytest.mark.asyncio
    async def test_analyze_department_relevance_json_parsing(self, mocker):
        """Test JSON response parsing from LLM."""
        # Arrange
        from src.utils.llm_helpers import analyze_department_relevance

        mock_call_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_call_llm.return_value = '''```json
{
  "decision": "include",
  "confidence": 85,
  "reasoning": "Strong alignment with ML research"
}
```'''

        # Act
        result = await analyze_department_relevance(
            department_name="Computer Science",
            school="Engineering",
            research_interests="Machine learning and AI",
            degree="PhD CS",
            background="BS CS",
            correlation_id="test-123"
        )

        # Assert
        assert result["decision"] == "include"
        assert result["confidence"] == 85
        assert "Strong alignment" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_analyze_department_relevance_malformed_json(self, mocker):
        """Test handling of malformed JSON response."""
        # Arrange
        from src.utils.llm_helpers import analyze_department_relevance

        mock_call_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_call_llm.return_value = "This is not valid JSON"

        # Act
        result = await analyze_department_relevance(
            department_name="Computer Science",
            school="Engineering",
            research_interests="Machine learning",
            degree="PhD CS",
            background="BS CS",
            correlation_id="test-123"
        )

        # Assert
        # Should default to exclude on parse error
        assert result["decision"] == "exclude"
        assert result["confidence"] == 0
        assert "JSON parse error" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_analyze_department_relevance_missing_fields(self, mocker):
        """Test handling of JSON with missing required fields."""
        # Arrange
        from src.utils.llm_helpers import analyze_department_relevance

        mock_call_llm = mocker.patch('src.utils.llm_helpers.call_llm_with_retry')
        mock_call_llm.return_value = '{"decision": "include"}'  # Missing confidence and reasoning

        # Act
        result = await analyze_department_relevance(
            department_name="Computer Science",
            school="Engineering",
            research_interests="Machine learning",
            degree="PhD CS",
            background="BS CS",
            correlation_id="test-123"
        )

        # Assert
        # Should return default values for invalid response
        assert result["decision"] == "exclude"
        assert result["confidence"] == 0
        assert "Invalid response format" in result["reasoning"]

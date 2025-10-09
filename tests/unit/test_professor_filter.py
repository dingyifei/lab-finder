"""Unit tests for professor filtering functionality (Story 3.2).

Tests cover:
1. Filter orchestration with mock LLM responses
2. Inclusive filtering (ANY overlap includes professor)
3. Exclusion of unrelated professors
4. Interdisciplinary researcher handling
5. Edge cases (emerging fields, missing research areas)
6. Batch processing and checkpoint saving
7. Confidence score assignment
"""

import pytest
from unittest.mock import Mock, patch

from src.agents.professor_filtering import (
    load_user_profile,
    format_profile_for_llm,
    filter_professor_single,
    filter_professors,
)
from src.models.professor import Professor


class TestLoadUserProfile:
    """Test user profile loading from markdown file."""

    def test_load_user_profile_success(self, tmp_path):
        """Test successful profile loading with all fields."""
        # Arrange
        profile_path = tmp_path / "output" / "user_profile.md"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(
            """
# Research Profile: Test User

**Current Position:** PhD in Computer Science

### Streamlined Research Focus

Machine learning and artificial intelligence with focus on deep learning.

---
            """,
            encoding="utf-8",
        )

        # Act
        with patch("src.agents.professor_filtering.Path") as mock_path:
            mock_path.return_value = profile_path
            result = load_user_profile()

        # Assert
        assert (
            result["research_interests"]
            == "Machine learning and artificial intelligence with focus on deep learning."
        )
        assert result["current_degree"] == "PhD in Computer Science"

    def test_load_user_profile_missing_file(self, tmp_path):
        """Test error when profile file doesn't exist."""
        # Arrange - Use a path that doesn't exist
        non_existent_path = tmp_path / "nonexistent" / "user_profile.md"

        # Act & Assert
        with patch("src.agents.professor_filtering.Path") as mock_path:
            mock_path.return_value = non_existent_path
            with pytest.raises(
                FileNotFoundError, match="User profile must be generated"
            ):
                load_user_profile()

    def test_load_user_profile_missing_interests(self, tmp_path):
        """Test error when research interests are missing."""
        # Arrange
        profile_path = tmp_path / "output" / "user_profile.md"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(
            """
# Research Profile: Test User

**Current Position:** PhD in Computer Science
            """,
            encoding="utf-8",
        )

        # Act & Assert
        with patch("src.agents.professor_filtering.Path") as mock_path:
            mock_path.return_value = profile_path
            with pytest.raises(
                ValueError, match="Cannot filter professors without research interests"
            ):
                load_user_profile()

    def test_load_user_profile_missing_degree(self, tmp_path):
        """Test fallback when degree is missing."""
        # Arrange
        profile_path = tmp_path / "output" / "user_profile.md"
        profile_path.parent.mkdir(parents=True)
        profile_path.write_text(
            """
# Research Profile: Test User

### Streamlined Research Focus

Machine learning research.
            """,
            encoding="utf-8",
        )

        # Act
        with patch("src.agents.professor_filtering.Path") as mock_path:
            mock_path.return_value = profile_path
            result = load_user_profile()

        # Assert
        assert result["current_degree"] == "General"


class TestFormatProfileForLLM:
    """Test profile formatting for LLM input."""

    def test_format_profile_for_llm(self):
        """Test profile dict formatting."""
        # Arrange
        profile_dict = {
            "research_interests": "Machine learning and AI",
            "current_degree": "PhD in CS",
        }

        # Act
        result = format_profile_for_llm(profile_dict)

        # Assert
        assert "Research Interests: Machine learning and AI" in result
        assert "Degree Program: PhD in CS" in result


@pytest.mark.asyncio
class TestFilterProfessorSingle:
    """Test single professor filtering with various scenarios."""

    async def test_filter_includes_relevant_professor(self, mocker):
        """Test 1: Inclusive filtering - high confidence includes professor."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {
            "confidence": 85,
            "reasoning": "Strong overlap in ML research",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-1",
            name="Dr. Jane Smith",
            title="Professor",
            department_id="cs-001",
            department_name="Computer Science",
            research_areas=["Machine Learning", "Deep Learning"],
            profile_url="https://example.edu/faculty/smith",
        )

        profile_dict = {
            "research_interests": "Machine Learning and AI",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert
        assert result["decision"] == "include"
        assert result["confidence"] == 85
        assert "Strong overlap" in result["reasoning"]
        mock_llm.assert_called_once()

    async def test_filter_excludes_unrelated_professor(self, mocker):
        """Test 3: Exclusion - low confidence excludes professor."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {
            "confidence": 15,
            "reasoning": "No overlap - English literature vs ML",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-2",
            name="Dr. John Doe",
            title="Professor",
            department_id="eng-001",
            department_name="English",
            research_areas=["Victorian Literature", "Poetry"],
            profile_url="https://example.edu/faculty/doe",
        )

        profile_dict = {
            "research_interests": "Machine Learning and AI",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert
        assert result["decision"] == "exclude"
        assert result["confidence"] == 15

    async def test_filter_interdisciplinary_professor(self, mocker):
        """Test 4: Interdisciplinary - multiple research areas with overlap."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {
            "confidence": 78,
            "reasoning": "Computational biology overlaps with ML",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-3",
            name="Dr. Alice Johnson",
            title="Associate Professor",
            department_id="bio-001",
            department_name="Biology",
            research_areas=["Computational Biology", "Bioinformatics", "Genomics"],
            profile_url="https://example.edu/faculty/johnson",
        )

        profile_dict = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert
        assert result["decision"] == "include"  # confidence >= 70
        assert result["confidence"] == 78

    async def test_filter_missing_research_areas(self, mocker):
        """Test 5: Edge case - professor with no research areas listed."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {
            "confidence": 50,
            "reasoning": "No research areas specified",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-4",
            name="Dr. Bob Williams",
            title="Assistant Professor",
            department_id="cs-001",
            department_name="Computer Science",
            research_areas=[],  # No research areas
            profile_url="https://example.edu/faculty/williams",
        )

        profile_dict = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert
        # Low confidence, should exclude
        assert result["decision"] == "exclude"
        mock_llm.assert_called_once()
        # Check that "Not specified" was passed to LLM
        call_args = mock_llm.call_args
        assert call_args[1]["research_areas"] == "Not specified"

    async def test_filter_llm_failure_fallback(self, mocker):
        """Test LLM failure handling - inclusive fallback."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.side_effect = Exception("LLM service unavailable")

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-5",
            name="Dr. Carol Davis",
            title="Professor",
            department_id="cs-001",
            department_name="Computer Science",
            research_areas=["Quantum Computing"],
            profile_url="https://example.edu/faculty/davis",
        )

        profile_dict = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert - inclusive fallback
        assert result["decision"] == "include"
        assert result["confidence"] == 0
        assert "LLM call failed" in result["reasoning"]

    async def test_filter_emerging_field(self, mocker):
        """Test 5: Edge case - emerging field with conceptual overlap."""
        # Arrange
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {
            "confidence": 72,
            "reasoning": "Quantum ML is emerging field related to ML",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_system_params.return_value = mock_params

        professor = Professor(
            id="prof-6",
            name="Dr. Eve Martinez",
            title="Assistant Professor",
            department_id="physics-001",
            department_name="Physics",
            research_areas=["Quantum Machine Learning"],
            profile_url="https://example.edu/faculty/martinez",
        )

        profile_dict = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        # Act
        result = await filter_professor_single(professor, profile_dict, "test-corr-id")

        # Assert
        assert result["decision"] == "include"
        assert result["confidence"] >= 70


@pytest.mark.asyncio
class TestFilterProfessors:
    """Test batch orchestration and checkpoint handling."""

    async def test_filter_professors_batch_processing(self, mocker):
        """Test 6: Batch processing and checkpoint saving."""
        # Arrange - Mock user profile loading
        mock_load_profile = mocker.patch(
            "src.agents.professor_filtering.load_user_profile"
        )
        mock_load_profile.return_value = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        # Mock system params
        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.batch_config.professor_filtering_batch_size = 2
        mock_params.rate_limiting.max_concurrent_llm_calls = 3
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_params.filtering_config.high_confidence_threshold = 90
        mock_system_params.return_value = mock_params

        # Mock checkpoint manager
        mock_checkpoint = mocker.patch("src.agents.professor_filtering.CheckpointManager")
        mock_checkpoint_instance = Mock()
        mock_checkpoint.return_value = mock_checkpoint_instance

        # Create test professors
        test_professors = [
            {
                "id": "prof-1",
                "name": "Dr. Jane Smith",
                "title": "Professor",
                "department_id": "cs-001",
                "department_name": "Computer Science",
                "research_areas": ["Machine Learning"],
                "profile_url": "https://example.edu/smith",
                "data_quality_flags": [],
            },
            {
                "id": "prof-2",
                "name": "Dr. John Doe",
                "title": "Professor",
                "department_id": "eng-001",
                "department_name": "English",
                "research_areas": ["Literature"],
                "profile_url": "https://example.edu/doe",
                "data_quality_flags": [],
            },
        ]

        mock_checkpoint_instance.load_batches.return_value = test_professors
        mock_checkpoint_instance.get_resume_point.return_value = 0

        # Mock LLM responses
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.side_effect = [
            {"confidence": 85, "reasoning": "Strong ML match"},
            {"confidence": 15, "reasoning": "No overlap"},
        ]

        # Mock progress tracker
        mock_tracker = mocker.patch("src.agents.professor_filtering.ProgressTracker")
        mock_tracker_instance = Mock()
        mock_tracker.return_value = mock_tracker_instance

        # Mock additional Story 3.3/3.4 functions
        mocker.patch("src.utils.confidence.apply_manual_overrides", return_value=0)
        mocker.patch(
            "src.utils.confidence.calculate_confidence_stats",
            return_value={
                "total_professors": 2,
                "included": {"high": 1, "medium": 0, "low": 0},
                "excluded": {"high": 0, "medium": 0, "low": 1},
                "distribution_analysis": {"quality_assessment": "Good"},
            },
        )
        mocker.patch("src.utils.confidence.save_confidence_stats_report")

        # Act
        result = await filter_professors("test-correlation-id")

        # Assert
        assert len(result) == 2
        assert result[0].is_relevant is True  # ML professor included
        assert result[0].relevance_confidence == 85
        assert result[1].is_relevant is False  # English professor excluded
        assert result[1].relevance_confidence == 15

        # Verify checkpoint saving was called
        assert mock_checkpoint_instance.save_batch.called

        # Verify progress tracking
        assert mock_tracker_instance.start_phase.called
        assert mock_tracker_instance.complete_phase.called

    async def test_filter_professors_confidence_scoring(self, mocker):
        """Test 7: Confidence score assignment and thresholding."""
        # Arrange
        mock_load_profile = mocker.patch(
            "src.agents.professor_filtering.load_user_profile"
        )
        mock_load_profile.return_value = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.batch_config.professor_filtering_batch_size = 10
        mock_params.rate_limiting.max_concurrent_llm_calls = 3
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_params.filtering_config.high_confidence_threshold = 90
        mock_system_params.return_value = mock_params

        mock_checkpoint = mocker.patch("src.agents.professor_filtering.CheckpointManager")
        mock_checkpoint_instance = Mock()
        mock_checkpoint.return_value = mock_checkpoint_instance

        # Test professor
        test_professor = {
            "id": "prof-1",
            "name": "Dr. Test",
            "title": "Professor",
            "department_id": "cs-001",
            "department_name": "CS",
            "research_areas": ["AI"],
            "profile_url": "https://example.edu/test",
            "data_quality_flags": [],
        }

        mock_checkpoint_instance.load_batches.return_value = [test_professor]
        mock_checkpoint_instance.get_resume_point.return_value = 0

        # Mock LLM with threshold-boundary confidence
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.return_value = {"confidence": 70, "reasoning": "Exact threshold match"}

        mocker.patch("src.agents.professor_filtering.ProgressTracker")

        # Act
        result = await filter_professors("test-correlation-id")

        # Assert - confidence == 70 should be included (>= threshold)
        assert len(result) == 1
        assert result[0].relevance_confidence == 70
        assert result[0].is_relevant is True

    async def test_filter_professors_empty_list(self, mocker):
        """Test edge case: empty professor list."""
        # Arrange
        mock_load_profile = mocker.patch(
            "src.agents.professor_filtering.load_user_profile"
        )
        mock_load_profile.return_value = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.batch_config.professor_filtering_batch_size = 10
        mock_params.rate_limiting.max_concurrent_llm_calls = 3
        mock_system_params.return_value = mock_params

        mock_checkpoint = mocker.patch("src.agents.professor_filtering.CheckpointManager")
        mock_checkpoint_instance = Mock()
        mock_checkpoint.return_value = mock_checkpoint_instance
        mock_checkpoint_instance.load_batches.return_value = []
        mock_checkpoint_instance.get_resume_point.return_value = 0

        mocker.patch("src.agents.professor_filtering.ProgressTracker")

        # Act
        result = await filter_professors("test-correlation-id")

        # Assert
        assert len(result) == 0

    async def test_filter_professors_data_quality_flags(self, mocker):
        """Test that data quality flags are added correctly."""
        # Arrange
        mock_load_profile = mocker.patch(
            "src.agents.professor_filtering.load_user_profile"
        )
        mock_load_profile.return_value = {
            "research_interests": "Machine Learning",
            "current_degree": "PhD in CS",
        }

        mock_system_params = mocker.patch(
            "src.agents.professor_filtering.SystemParams.load"
        )
        mock_params = Mock()
        mock_params.batch_config.professor_filtering_batch_size = 10
        mock_params.rate_limiting.max_concurrent_llm_calls = 3
        mock_params.confidence_thresholds.professor_filter = 70.0
        mock_params.filtering_config.low_confidence_threshold = 70
        mock_params.filtering_config.high_confidence_threshold = 90
        mock_system_params.return_value = mock_params

        mock_checkpoint = mocker.patch("src.agents.professor_filtering.CheckpointManager")
        mock_checkpoint_instance = Mock()
        mock_checkpoint.return_value = mock_checkpoint_instance

        test_professor = {
            "id": "prof-1",
            "name": "Dr. Test",
            "title": "Professor",
            "department_id": "cs-001",
            "department_name": "CS",
            "research_areas": ["AI"],
            "profile_url": "https://example.edu/test",
            "data_quality_flags": [],
        }

        mock_checkpoint_instance.load_batches.return_value = [test_professor]
        mock_checkpoint_instance.get_resume_point.return_value = 0

        # Mock LLM failure (confidence = 0)
        mock_llm = mocker.patch("src.agents.professor_filtering.filter_professor_research")
        mock_llm.side_effect = Exception("LLM failed")

        mocker.patch("src.agents.professor_filtering.ProgressTracker")

        # Act
        result = await filter_professors("test-correlation-id")

        # Assert - should have llm_filtering_failed flag
        assert len(result) == 1
        assert "llm_filtering_failed" in result[0].data_quality_flags
        assert result[0].relevance_confidence == 0
        assert result[0].is_relevant is True  # Inclusive fallback

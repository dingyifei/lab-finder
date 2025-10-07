"""
Unit tests for ProfileConsolidator
"""

import json
from pathlib import Path
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, patch

from src.agents.profile_consolidator import ProfileConsolidator
from src.models.profile import ConsolidatedProfile


@pytest.fixture
def sample_user_profile_full():
    """Full user profile with all fields."""
    return {
        "name": "Jane Doe",
        "current_degree": "PhD in Computer Science",
        "target_university": "Stanford University",
        "target_department": "Computer Science",
        "research_interests": [
            "Machine Learning",
            "Natural Language Processing",
            "Artificial Intelligence",
        ],
        "resume_highlights": {
            "education": [
                {
                    "degree": "MS in Computer Science",
                    "institution": "University of California, Berkeley",
                    "year": 2022,
                },
                {"degree": "BS in Mathematics", "institution": "MIT", "year": 2020},
            ],
            "skills": ["Python", "TensorFlow", "PyTorch", "Research Writing"],
            "research_experience": [
                {
                    "title": "Research Assistant - NLP Lab",
                    "description": "Developed transformer models for question answering",
                    "duration": "2021-2022",
                }
            ],
        },
        "preferred_graduation_duration": 5.5,
    }


@pytest.fixture
def sample_user_profile_minimal():
    """Minimal user profile with only required fields."""
    return {
        "name": "John Smith",
        "current_degree": "PhD in Biology",
        "target_university": "Harvard University",
        "target_department": "Molecular Biology",
        "research_interests": ["Genomics"],
    }


@pytest.fixture
def sample_university_config():
    """Sample university configuration."""
    return {
        "university_name": "Stanford University",
        "core_website": "https://www.stanford.edu",
        "directory_link": "https://www.stanford.edu/directory",
    }


@pytest.fixture
def consolidator(tmp_path):
    """ProfileConsolidator instance with temp output directory."""
    return ProfileConsolidator(output_dir=tmp_path)


class TestProfileConsolidation:
    """Test profile consolidation functionality."""

    @pytest.mark.asyncio
    async def test_consolidate_profile_with_full_data(
        self, consolidator, sample_user_profile_full, sample_university_config
    ):
        """Test consolidation with complete data."""
        # Arrange
        mock_llm_response = (
            "Jane Doe's research focuses on advancing machine learning and "
            "natural language processing techniques with applications in "
            "artificial intelligence."
        )

        with patch(
            "src.agents.profile_consolidator.call_llm_with_retry",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # Act
            profile = await consolidator.consolidate(
                sample_user_profile_full, sample_university_config
            )

            # Assert
            assert profile.name == "Jane Doe"
            assert profile.current_degree == "PhD in Computer Science"
            assert profile.target_university == "Stanford University"
            assert profile.target_department == "Computer Science"
            assert len(profile.research_interests) == 3
            assert profile.streamlined_interests == mock_llm_response
            assert "MS in Computer Science" in profile.education_background
            assert "Berkeley" in profile.education_background
            assert "Python" in profile.skills_summary
            assert "PyTorch" in profile.skills_summary
            assert "Research Assistant" in profile.research_experience_summary
            assert len(profile.key_qualifications) == 4
            assert profile.preferred_graduation_duration == 5.5
            assert profile.university_website == "https://www.stanford.edu"
            assert profile.generated_at is not None

            # Verify LLM was called
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_consolidate_profile_with_minimal_data(
        self, consolidator, sample_user_profile_minimal, sample_university_config
    ):
        """Test consolidation with minimal required data."""
        # Arrange
        mock_llm_response = "John Smith's research focuses on genomics."

        with patch(
            "src.agents.profile_consolidator.call_llm_with_retry",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # Act
            profile = await consolidator.consolidate(
                sample_user_profile_minimal, sample_university_config
            )

            # Assert
            assert profile.name == "John Smith"
            assert profile.education_background == "Education details not provided"
            assert profile.skills_summary == "Skills not provided"
            assert (
                profile.research_experience_summary
                == "Research experience not provided"
            )
            assert len(profile.key_qualifications) == 2  # degree + interests count
            assert profile.preferred_graduation_duration == 5.5  # default

    @pytest.mark.asyncio
    async def test_llm_interest_streamlining(
        self, consolidator, sample_user_profile_full, sample_university_config
    ):
        """Test LLM interest streamlining with retry."""
        # Arrange
        mock_llm_response = "Streamlined research interests summary."

        with patch(
            "src.agents.profile_consolidator.call_llm_with_retry",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = mock_llm_response

            # Act
            profile = await consolidator.consolidate(
                sample_user_profile_full, sample_university_config
            )

            # Assert
            assert profile.streamlined_interests == mock_llm_response
            mock_llm.assert_called_once()

            # Verify prompt contains research interests
            call_args = mock_llm.call_args
            prompt = call_args[0][0]
            assert "Machine Learning" in prompt
            assert "Natural Language Processing" in prompt

    @pytest.mark.asyncio
    async def test_llm_failure_propagates(
        self, consolidator, sample_user_profile_full, sample_university_config
    ):
        """Test that LLM failures propagate correctly."""
        # Arrange
        with patch(
            "src.agents.profile_consolidator.call_llm_with_retry",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.side_effect = Exception("LLM call failed")

            # Act & Assert
            with pytest.raises(Exception, match="LLM call failed"):
                await consolidator.consolidate(
                    sample_user_profile_full, sample_university_config
                )


class TestEducationExtraction:
    """Test education extraction functionality."""

    def test_extract_education_with_multiple_entries(self, consolidator):
        """Test extraction with multiple education entries."""
        # Arrange
        resume = {
            "education": [
                {"degree": "PhD", "institution": "MIT", "year": 2023},
                {"degree": "MS", "institution": "Stanford", "year": 2020},
            ]
        }

        # Act
        result = consolidator._extract_education(resume)

        # Assert
        assert "PhD, MIT (2023)" in result
        assert "MS, Stanford (2020)" in result
        assert ";" in result

    def test_extract_education_without_year(self, consolidator):
        """Test extraction when year is missing."""
        # Arrange
        resume = {"education": [{"degree": "BS", "institution": "Harvard"}]}

        # Act
        result = consolidator._extract_education(resume)

        # Assert
        assert "BS, Harvard" in result
        assert "(" not in result

    def test_extract_education_empty(self, consolidator):
        """Test extraction with no education data."""
        # Arrange
        resume = {}

        # Act
        result = consolidator._extract_education(resume)

        # Assert
        assert result == "Education details not provided"


class TestSkillsExtraction:
    """Test skills extraction functionality."""

    def test_extract_skills_with_list(self, consolidator):
        """Test extraction with skills list."""
        # Arrange
        resume = {"skills": ["Python", "Java", "Machine Learning", "Data Analysis"]}

        # Act
        result = consolidator._extract_skills(resume)

        # Assert
        assert "Python" in result
        assert "Java" in result
        assert "Machine Learning" in result
        assert ", " in result

    def test_extract_skills_empty(self, consolidator):
        """Test extraction with no skills data."""
        # Arrange
        resume = {}

        # Act
        result = consolidator._extract_skills(resume)

        # Assert
        assert result == "Skills not provided"


class TestResearchExperienceExtraction:
    """Test research experience extraction functionality."""

    def test_extract_experience_with_multiple_entries(self, consolidator):
        """Test extraction with multiple experience entries."""
        # Arrange
        resume = {
            "research_experience": [
                {
                    "title": "Research Assistant",
                    "description": "NLP research",
                    "duration": "2021-2022",
                },
                {
                    "title": "PhD Candidate",
                    "description": "ML research",
                    "duration": "2022-2024",
                },
            ]
        }

        # Act
        result = consolidator._extract_research_experience(resume)

        # Assert
        assert "Research Assistant (2021-2022): NLP research" in result
        assert "PhD Candidate (2022-2024): ML research" in result
        assert ";" in result

    def test_extract_experience_without_duration(self, consolidator):
        """Test extraction when duration is missing."""
        # Arrange
        resume = {
            "research_experience": [{"title": "Intern", "description": "Research work"}]
        }

        # Act
        result = consolidator._extract_research_experience(resume)

        # Assert
        assert "Intern: Research work" in result
        assert "(" not in result

    def test_extract_experience_empty(self, consolidator):
        """Test extraction with no experience data."""
        # Arrange
        resume = {}

        # Act
        result = consolidator._extract_research_experience(resume)

        # Assert
        assert result == "Research experience not provided"


class TestQualificationsExtraction:
    """Test qualifications extraction functionality."""

    def test_extract_qualifications_full(self, consolidator):
        """Test extraction with all qualification types."""
        # Arrange
        profile = {
            "current_degree": "PhD in CS",
            "research_interests": ["AI", "ML", "NLP"],
            "resume_highlights": {
                "skills": ["Python", "Java"],
                "research_experience": [{"title": "RA"}],
            },
        }

        # Act
        result = consolidator._extract_qualifications(profile)

        # Assert
        assert len(result) == 4
        assert "Currently pursuing PhD in CS" in result
        assert "3 primary research interest area(s)" in result
        assert "2 technical skills" in result
        assert "1 research experience(s)" in result

    def test_extract_qualifications_minimal(self, consolidator):
        """Test extraction with minimal data."""
        # Arrange
        profile = {
            "current_degree": "PhD in Biology",
            "research_interests": ["Genomics"],
        }

        # Act
        result = consolidator._extract_qualifications(profile)

        # Assert
        assert len(result) == 2
        assert "Currently pursuing PhD in Biology" in result
        assert "1 primary research interest area(s)" in result


class TestMarkdownGeneration:
    """Test markdown file generation."""

    def test_save_markdown_creates_file(self, consolidator, sample_user_profile_full):
        """Test markdown file creation."""
        # Arrange
        profile = ConsolidatedProfile(
            name="Jane Doe",
            current_degree="PhD in CS",
            target_university="Stanford",
            target_department="Computer Science",
            research_interests=["ML", "NLP"],
            streamlined_interests="Research focus summary",
            education_background="MS in CS, Berkeley",
            skills_summary="Python, PyTorch",
            research_experience_summary="RA position",
            key_qualifications=["PhD student", "2 research areas"],
            preferred_graduation_duration=5.5,
            university_website="https://stanford.edu",
            generated_at=datetime.utcnow().isoformat(),
        )

        # Act
        output_path = consolidator.save_markdown(profile)

        # Assert
        assert output_path.exists()
        assert output_path.name == "user_profile.md"

        # Read and verify content
        content = output_path.read_text(encoding="utf-8")
        assert "# Research Profile: Jane Doe" in content
        assert "PhD in CS" in content
        assert "Stanford" in content
        assert "Research focus summary" in content
        assert "MS in CS, Berkeley" in content
        assert "Python, PyTorch" in content

    def test_markdown_contains_all_sections(
        self, consolidator, sample_user_profile_full
    ):
        """Test markdown contains all required sections."""
        # Arrange
        profile = ConsolidatedProfile(
            name="Test User",
            current_degree="PhD",
            target_university="University",
            target_department="Department",
            research_interests=["Interest 1"],
            streamlined_interests="Summary",
            education_background="Education",
            skills_summary="Skills",
            research_experience_summary="Experience",
            key_qualifications=["Qual 1"],
            preferred_graduation_duration=5.0,
            university_website="https://example.edu",
            generated_at=datetime.utcnow().isoformat(),
        )

        # Act
        output_path = consolidator.save_markdown(profile)
        content = output_path.read_text(encoding="utf-8")

        # Assert
        assert "## Overview" in content
        assert "## Research Interests" in content
        assert "### Streamlined Research Focus" in content
        assert "## Academic Background" in content
        assert "### Education" in content
        assert "### Skills" in content
        assert "### Research Experience" in content
        assert "## Key Qualifications" in content
        assert "## Configuration" in content
        assert "## Usage" in content


class TestCheckpointSaving:
    """Test checkpoint saving functionality."""

    def test_save_checkpoint_creates_file(self, consolidator):
        """Test checkpoint file creation."""
        # Arrange
        profile = ConsolidatedProfile(
            name="Jane Doe",
            current_degree="PhD in CS",
            target_university="Stanford",
            target_department="Computer Science",
            research_interests=["ML"],
            streamlined_interests="Summary",
            education_background="MS in CS",
            skills_summary="Python",
            research_experience_summary="RA",
            key_qualifications=["PhD student"],
            preferred_graduation_duration=5.5,
            university_website="https://stanford.edu",
            generated_at=datetime.utcnow().isoformat(),
        )

        # Act
        consolidator.save_checkpoint(profile)

        # Assert
        checkpoint_path = Path("checkpoints/phase-0-validation.json")
        assert checkpoint_path.exists()

        # Read and verify checkpoint
        checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert checkpoint_data["name"] == "Jane Doe"
        assert checkpoint_data["current_degree"] == "PhD in CS"
        assert "ML" in checkpoint_data["research_interests"]

    def test_checkpoint_contains_all_fields(self, consolidator):
        """Test checkpoint contains all profile fields."""
        # Arrange
        profile = ConsolidatedProfile(
            name="Test User",
            current_degree="PhD",
            target_university="University",
            target_department="Department",
            research_interests=["Interest 1", "Interest 2"],
            streamlined_interests="Summary",
            education_background="Education",
            skills_summary="Skills",
            research_experience_summary="Experience",
            key_qualifications=["Qual 1", "Qual 2"],
            preferred_graduation_duration=5.0,
            university_website="https://example.edu",
            generated_at="2024-01-01T00:00:00",
        )

        # Act
        consolidator.save_checkpoint(profile)

        # Assert
        checkpoint_path = Path("checkpoints/phase-0-validation.json")
        checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))

        # Verify all fields present
        assert "name" in checkpoint_data
        assert "current_degree" in checkpoint_data
        assert "target_university" in checkpoint_data
        assert "target_department" in checkpoint_data
        assert "research_interests" in checkpoint_data
        assert "streamlined_interests" in checkpoint_data
        assert "education_background" in checkpoint_data
        assert "skills_summary" in checkpoint_data
        assert "research_experience_summary" in checkpoint_data
        assert "key_qualifications" in checkpoint_data
        assert "preferred_graduation_duration" in checkpoint_data
        assert "university_website" in checkpoint_data
        assert "generated_at" in checkpoint_data

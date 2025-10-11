"""
Unit tests for llm_helpers module.
"""

import pytest
from unittest.mock import AsyncMock
from src.utils.llm_helpers import (
    call_llm_with_retry,
    analyze_department_relevance,
    filter_professor_research,
    match_linkedin_profile,
    match_names,
    score_abstract_relevance,
)
from src.utils.prompt_loader import render_prompt


class TestPromptTemplates:
    """Test cases for prompt template formatting."""

    def test_department_relevance_template_formatting(self):
        """Test that department relevance template formats correctly."""
        # Arrange
        interests = "machine learning, AI"
        degree = "PhD Computer Science"
        background = "BS in Computer Science"
        department_name = "Computer Science"
        school = "Engineering"

        # Act
        prompt = render_prompt(
            "department/relevance_filter.j2",
            interests=interests,
            degree=degree,
            background=background,
            department_name=department_name,
            school=school,
        )

        # Assert
        assert "machine learning, AI" in prompt
        assert "PhD Computer Science" in prompt
        assert "BS in Computer Science" in prompt
        assert "Computer Science" in prompt
        assert "Engineering" in prompt
        assert "JSON" in prompt  # Updated to match actual template
        assert "decision" in prompt
        assert "confidence" in prompt
        assert "reasoning" in prompt

    def test_professor_filter_template_formatting(self):
        """Test that professor filter template formats correctly."""
        # Arrange
        profile = "PhD student in ML"
        name = "Dr. Jane Smith"
        research_areas = "deep learning, NLP"
        bio = "Professor of CS"

        # Act
        prompt = render_prompt(
            "professor/research_filter.j2",
            profile=profile,
            name=name,
            research_areas=research_areas,
            bio=bio,
        )

        # Assert
        assert "PhD student in ML" in prompt
        assert "Dr. Jane Smith" in prompt
        assert "deep learning, NLP" in prompt
        assert "Professor of CS" in prompt
        assert (
            "confidence" in prompt
        )  # Updated to match actual template (lowercase in JSON spec)

    def test_linkedin_match_template_formatting(self):
        """Test that LinkedIn match template formats correctly."""
        # Arrange
        member_name = "John Doe"
        university = "Stanford University"
        lab_name = "AI Lab"
        profile_data = "Software Engineer at Google"

        # Act
        prompt = render_prompt(
            "linkedin/profile_match.j2",
            member_name=member_name,
            university=university,
            lab_name=lab_name,
            profile_data=profile_data,
        )

        # Assert
        assert "John Doe" in prompt
        assert "Stanford University" in prompt
        assert "AI Lab" in prompt
        assert "Software Engineer at Google" in prompt

    def test_name_match_template_formatting(self):
        """Test that name match template formats correctly."""
        # Arrange
        name1 = "J. Smith"
        name2 = "Jane Smith"
        context = "Both at Stanford CS"

        # Act
        prompt = render_prompt(
            "professor/name_match.j2", name1=name1, name2=name2, context=context
        )

        # Assert
        assert "J. Smith" in prompt
        assert "Jane Smith" in prompt
        assert "Both at Stanford CS" in prompt

    def test_abstract_relevance_template_formatting(self):
        """Test that abstract relevance template formats correctly."""
        # Arrange
        interests = "machine learning"
        abstract = "We propose a new ML algorithm..."
        title = "Novel ML Approach"

        # Act
        prompt = render_prompt(
            "publication/abstract_relevance.j2",
            interests=interests,
            abstract=abstract,
            title=title,
        )

        # Assert
        assert "machine learning" in prompt
        assert "We propose a new ML algorithm..." in prompt
        assert "Novel ML Approach" in prompt


class TestCallLLMWithRetry:
    """Test cases for call_llm_with_retry function."""

    @pytest.mark.asyncio
    async def test_llm_call_succeeds(self, mocker):
        """Test that call_llm_with_retry successfully calls ClaudeSDKClient."""
        # Arrange
        prompt = "Test prompt"

        # Mock the response message
        mock_message = mocker.Mock()
        mock_block = mocker.Mock()
        mock_block.text = "Test LLM response"
        mock_message.content = [mock_block]

        # Create async generator for mock response
        async def mock_receive_response():
            yield mock_message

        # Create mock client
        mock_client = mocker.AsyncMock()
        mock_client.query = mocker.AsyncMock()
        mock_client.receive_response = mock_receive_response
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock(return_value=None)

        # Patch ClaudeSDKClient from claude_agent_sdk module
        mock_client_class = mocker.patch("claude_agent_sdk.ClaudeSDKClient")
        mock_client_class.return_value = mock_client

        # Act
        response = await call_llm_with_retry(prompt)

        # Assert
        assert response == "Test LLM response"
        mock_client.query.assert_called_once_with(prompt)


class TestAnalyzeDepartmentRelevance:
    """Test cases for analyze_department_relevance function."""

    @pytest.mark.asyncio
    async def test_parses_llm_response_correctly(self, mocker):
        """Test that analyze_department_relevance parses LLM response."""
        # Arrange
        mock_response = '{"decision": "include", "confidence": 95, "reasoning": "Strong match for ML research"}'
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await analyze_department_relevance(
            department_name="Computer Science",
            school="Engineering",
            research_interests="machine learning",
            degree="PhD Computer Science",
            background="BS in Computer Science",
        )

        # Assert
        assert result["decision"] == "include"
        assert result["confidence"] == 95
        assert result["reasoning"] == "Strong match for ML research"


class TestFilterProfessorResearch:
    """Test cases for filter_professor_research function."""

    @pytest.mark.asyncio
    async def test_parses_confidence_score(self, mocker):
        """Test that filter_professor_research parses confidence score."""
        # Arrange
        mock_response = '{"confidence": 85, "reasoning": "Research areas align well"}'
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await filter_professor_research(
            professor_name="Dr. Smith",
            research_areas="machine learning",
            user_profile="PhD in ML",
        )

        # Assert
        assert result["confidence"] == 85
        assert result["reasoning"] == "Research areas align well"

    @pytest.mark.asyncio
    async def test_handles_invalid_confidence_score(self, mocker):
        """Test that filter_professor_research handles invalid confidence score."""
        # Arrange
        mock_response = "Confidence: invalid\nReasoning: Test"
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await filter_professor_research(
            professor_name="Dr. Smith",
            research_areas="machine learning",
            user_profile="PhD in ML",
        )

        # Assert
        assert result["confidence"] == 0  # Default on parse error


class TestMatchLinkedInProfile:
    """Test cases for match_linkedin_profile function."""

    @pytest.mark.asyncio
    async def test_parses_linkedin_match_result(self, mocker):
        """Test that match_linkedin_profile parses match result."""
        # Arrange
        mock_response = '{"confidence": 90, "reasoning": "Name and institution match"}'
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await match_linkedin_profile(
            member_name="John Doe",
            university="Stanford",
            lab_name="AI Lab",
            profile_data="PhD student at Stanford",
        )

        # Assert
        assert result["confidence"] == 90
        assert result["reasoning"] == "Name and institution match"


class TestMatchNames:
    """Test cases for match_names function."""

    @pytest.mark.asyncio
    async def test_parses_name_match_decision(self, mocker):
        """Test that match_names parses decision and confidence."""
        # Arrange
        mock_response = (
            '{"decision": "yes", "confidence": 95, "reasoning": "Same person"}'
        )
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await match_names(name1="J. Smith", name2="Jane Smith")

        # Assert
        assert result["decision"] == "yes"
        assert result["confidence"] == 95
        assert result["reasoning"] == "Same person"


class TestScoreAbstractRelevance:
    """Test cases for score_abstract_relevance function."""

    @pytest.mark.asyncio
    async def test_parses_relevance_score(self, mocker):
        """Test that score_abstract_relevance parses relevance score."""
        # Arrange
        mock_response = '{"relevance": 80, "reasoning": "Highly relevant to ML"}'
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await score_abstract_relevance(
            paper_title="ML Algorithm",
            abstract="We propose a new machine learning approach...",
            research_interests="machine learning",
        )

        # Assert
        assert result["relevance"] == 80
        assert result["reasoning"] == "Highly relevant to ML"

    @pytest.mark.asyncio
    async def test_handles_invalid_relevance_score(self, mocker):
        """Test that score_abstract_relevance handles invalid relevance score."""
        # Arrange
        mock_response = "Relevance: not_a_number\nReasoning: Test"
        mocker.patch(
            "src.utils.llm_helpers.call_llm_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        )

        # Act
        result = await score_abstract_relevance(
            paper_title="Test", abstract="Test abstract", research_interests="ML"
        )

        # Assert
        assert result["relevance"] == 0  # Default on parse error

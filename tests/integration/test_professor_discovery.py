"""Integration tests for professor discovery agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.professor_filter import (
    discover_professors_for_department,
    discover_with_playwright_fallback,
    generate_professor_id,
    load_relevant_departments,
    parse_professor_data,
)
from src.models.department import Department


@pytest.mark.integration
def test_generate_professor_id():
    """Test professor ID generation is deterministic."""
    name = "Dr. Jane Smith"
    dept_id = "dept-001"

    id1 = generate_professor_id(name, dept_id)
    id2 = generate_professor_id(name, dept_id)

    assert id1 == id2
    assert len(id1) == 16
    assert isinstance(id1, str)

    # Different name should produce different ID
    id3 = generate_professor_id("Dr. John Doe", dept_id)
    assert id3 != id1


@pytest.mark.integration
def test_parse_professor_data_valid_json():
    """Test parsing professor data from JSON response."""
    text = """
    Here are the professors I found:
    [
        {
            "name": "Dr. Jane Smith",
            "title": "Professor",
            "research_areas": ["Machine Learning", "AI"],
            "email": "jsmith@example.edu",
            "profile_url": "https://cs.edu/faculty/jsmith"
        },
        {
            "name": "Dr. John Doe",
            "title": "Associate Professor",
            "research_areas": ["Computer Vision"],
            "email": "jdoe@example.edu",
            "profile_url": "https://cs.edu/faculty/jdoe"
        }
    ]
    """

    result = parse_professor_data(text)
    assert len(result) == 2
    assert result[0]["name"] == "Dr. Jane Smith"
    assert result[0]["title"] == "Professor"
    assert result[1]["name"] == "Dr. John Doe"


@pytest.mark.integration
def test_parse_professor_data_no_json():
    """Test parsing professor data with no JSON returns empty list."""
    text = "No professors found on this page."
    result = parse_professor_data(text)
    assert result == []


@pytest.mark.integration
def test_parse_professor_data_invalid_json():
    """Test parsing professor data with invalid JSON returns empty list."""
    text = "[{invalid json}]"
    result = parse_professor_data(text)
    assert result == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discover_professors_with_mock_sdk(mocker):
    """Test discover_professors_for_department with mock ClaudeSDKClient."""
    from claude_agent_sdk import AssistantMessage, TextBlock

    # Create mock objects that will pass isinstance checks
    mock_text_block = MagicMock(spec=TextBlock)
    mock_text_block.text = """
    [
        {
            "name": "Dr. Jane Smith",
            "title": "Professor",
            "research_areas": ["Machine Learning", "AI"],
            "lab_name": "AI Lab",
            "lab_url": "https://ailab.edu",
            "email": "jsmith@example.edu",
            "profile_url": "https://cs.edu/faculty/jsmith"
        }
    ]
    """

    mock_message = MagicMock(spec=AssistantMessage)
    mock_message.content = [mock_text_block]

    # Mock async iterator for receive_response
    async def mock_receive_response():
        yield mock_message

    # Mock ClaudeSDKClient
    mock_client = AsyncMock()
    mock_client.query = AsyncMock()
    mock_client.receive_response = mock_receive_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Patch ClaudeSDKClient class
    mocker.patch(
        "src.agents.professor_filter.ClaudeSDKClient",
        return_value=mock_client,
    )

    dept = Department(
        id="dept-1",
        name="Computer Science",
        url="https://cs.edu/faculty",
        is_relevant=True,
    )

    professors = await discover_professors_for_department(dept, "test-corr-id")

    assert len(professors) > 0
    assert professors[0].name == "Dr. Jane Smith"
    assert professors[0].title == "Professor"
    assert professors[0].department_id == "dept-1"
    assert professors[0].lab_name == "AI Lab"
    assert "Machine Learning" in professors[0].research_areas


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discover_professors_invalid_url():
    """Test discover_professors_for_department with invalid URL."""
    dept = Department(
        id="dept-invalid",
        name="Invalid Department",
        url="not-a-url",
        is_relevant=True,
    )

    professors = await discover_professors_for_department(
        dept, "test-corr-id"
    )
    assert professors == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discover_professors_sdk_failure_triggers_playwright(mocker):
    """Test that WebFetch failure triggers Playwright fallback."""
    # Mock ClaudeSDKClient to raise exception
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(
        side_effect=Exception("WebFetch failed")
    )
    mocker.patch(
        "src.agents.professor_filter.ClaudeSDKClient",
        return_value=mock_client,
    )

    # Mock Playwright fallback to return empty list
    mocker.patch(
        "src.agents.professor_filter.discover_with_playwright_fallback",
        return_value=[],
    )

    dept = Department(
        id="dept-2",
        name="Biology",
        url="https://bio.edu/faculty",
        is_relevant=True,
    )

    professors = await discover_professors_for_department(dept, "test-corr-id")

    # Should call Playwright fallback
    assert professors == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_playwright_fallback_invalid_url():
    """Test Playwright fallback with invalid URL."""
    dept = Department(
        id="dept-invalid",
        name="Invalid Department",
        url="not-a-url",
        is_relevant=True,
    )

    professors = await discover_with_playwright_fallback(dept, "test-corr-id")
    assert professors == []


@pytest.mark.integration
def test_load_relevant_departments(mocker):
    """Test loading relevant departments from Epic 2 checkpoint."""
    # Mock checkpoint manager
    mock_checkpoint_manager = MagicMock()
    mock_checkpoint_manager.load_batches.return_value = [
        {
            "id": "dept-001",
            "name": "Computer Science",
            "school": "Engineering",
            "division": None,
            "url": "https://cs.edu",
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": True,
            "relevance_reasoning": "Strong match",
        },
        {
            "id": "dept-002",
            "name": "English",
            "school": "Arts",
            "division": None,
            "url": "https://english.edu",
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": False,
            "relevance_reasoning": "No match",
        },
        {
            "id": "dept-003",
            "name": "Biology",
            "school": "Science",
            "division": None,
            "url": "https://bio.edu",
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": True,
            "relevance_reasoning": "Good match",
        },
    ]

    mocker.patch(
        "src.agents.professor_filter.CheckpointManager",
        return_value=mock_checkpoint_manager,
    )

    departments = load_relevant_departments("test-corr-id")

    # Should only load relevant departments
    assert len(departments) == 2
    assert all(dept.is_relevant for dept in departments)
    assert departments[0].name == "Computer Science"
    assert departments[1].name == "Biology"


@pytest.mark.integration
def test_load_relevant_departments_filters_invalid(mocker):
    """Test that departments without required fields are filtered out."""
    # Mock checkpoint manager with some invalid departments
    mock_checkpoint_manager = MagicMock()
    mock_checkpoint_manager.load_batches.return_value = [
        {
            "id": "dept-001",
            "name": "Computer Science",
            "school": "Engineering",
            "division": None,
            "url": "https://cs.edu",
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": True,
            "relevance_reasoning": "Strong match",
        },
        {
            "id": "dept-002",
            "name": "",  # Missing name
            "school": "Arts",
            "division": None,
            "url": "https://arts.edu",
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": True,
            "relevance_reasoning": "Match",
        },
        {
            "id": "dept-003",
            "name": "Biology",
            "school": "Science",
            "division": None,
            "url": "",  # Missing URL
            "hierarchy_level": 1,
            "data_quality_flags": [],
            "is_relevant": True,
            "relevance_reasoning": "Match",
        },
    ]

    mocker.patch(
        "src.agents.professor_filter.CheckpointManager",
        return_value=mock_checkpoint_manager,
    )

    departments = load_relevant_departments("test-corr-id")

    # Should only include valid department
    assert len(departments) == 1
    assert departments[0].name == "Computer Science"

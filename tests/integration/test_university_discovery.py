"""Integration tests for University Discovery Agent."""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.agents.university_discovery import UniversityDiscoveryAgent
from src.models.department import Department
from src.utils.checkpoint_manager import CheckpointManager


@pytest.fixture
def mock_sdk_response():
    """Mock Claude Agent SDK JSON response."""
    return json.dumps([
        {
            "name": "Computer Science",
            "url": "https://example.edu/cs",
            "school": "School of Engineering",
            "division": None,
            "hierarchy_level": 2
        },
        {
            "name": "Electrical Engineering",
            "url": "https://example.edu/ee",
            "school": "School of Engineering",
            "division": None,
            "hierarchy_level": 2
        },
        {
            "name": "Mathematics",
            "url": "https://example.edu/math",
            "school": "School of Arts and Sciences",
            "division": None,
            "hierarchy_level": 2
        }
    ])


@pytest.fixture
def agent(tmp_path):
    """Create agent with temporary checkpoint directory."""
    checkpoint_manager = CheckpointManager(checkpoint_dir=tmp_path)
    return UniversityDiscoveryAgent(
        correlation_id="test-123",
        checkpoint_manager=checkpoint_manager,
        output_dir=tmp_path,
    )


def mock_sdk_query(response_text):
    """Helper to mock Claude Agent SDK query() function."""
    async def _mock_query(*args, **kwargs):
        # Create mock message objects
        mock_text_block = MagicMock()
        mock_text_block.text = response_text

        mock_message = MagicMock()
        mock_message.content = [mock_text_block]

        # Yield the message (async generator)
        yield mock_message

    return _mock_query


@pytest.mark.asyncio
async def test_discover_structure_success(agent, mock_sdk_response):
    """Test successful structure discovery with SDK."""
    with patch("claude_agent_sdk.query", new=mock_sdk_query(mock_sdk_response)):
        with patch("claude_agent_sdk.ClaudeAgentOptions"):
            with patch("claude_agent_sdk.AssistantMessage", MagicMock):
                with patch("claude_agent_sdk.TextBlock", MagicMock):
                    departments = await agent.discover_structure("https://example.edu")

                    assert len(departments) == 3
                    dept_names = [d.name for d in departments]
                    assert "Computer Science" in dept_names
                    assert "Electrical Engineering" in dept_names
                    assert "Mathematics" in dept_names


@pytest.mark.asyncio
async def test_discover_structure_sdk_with_markdown(agent):
    """Test SDK response with markdown code blocks."""
    # Test that SDK response with markdown code block formatting is properly parsed
    json_response = """[{
        "name": "Computer Science",
        "url": "https://example.edu/cs",
        "school": "Engineering",
        "division": null,
        "hierarchy_level": 2
    }]"""

    with patch("claude_agent_sdk.query", new=mock_sdk_query(f"```json\n{json_response}\n```")):
        with patch("claude_agent_sdk.ClaudeAgentOptions"):
            with patch("claude_agent_sdk.AssistantMessage", MagicMock):
                with patch("claude_agent_sdk.TextBlock", MagicMock):
                    departments = await agent.discover_structure("https://example.edu")

                    assert len(departments) == 1
                    assert departments[0].name == "Computer Science"


@pytest.mark.asyncio
async def test_discover_structure_sdk_failure_uses_fallback(agent, tmp_path):
    """Test graceful degradation when SDK fails - uses manual fallback."""
    # Mock SDK to raise an exception
    async def _mock_failing_query(*args, **kwargs):
        raise Exception("SDK connection failed")
        yield  # Make it a generator

    # Create manual fallback
    fallback_path = tmp_path / "fallback.json"
    fallback_data = {
        "departments": [
            {
                "name": "Computer Science",
                "url": "https://example.edu/cs",
                "school": "Engineering",
                "hierarchy_level": 1,
            }
        ]
    }
    with open(fallback_path, "w") as f:
        json.dump(fallback_data, f)

    with patch("claude_agent_sdk.query", new=_mock_failing_query):
        departments = await agent.discover_structure(
            "https://example.edu", manual_fallback_path=fallback_path
        )

        assert len(departments) == 1
        assert departments[0].name == "Computer Science"
        assert "manual_entry" in departments[0].data_quality_flags


@pytest.mark.asyncio
async def test_discover_structure_no_departments_in_response(agent):
    """Test when SDK returns empty response."""
    empty_response = "[]"

    with patch("claude_agent_sdk.query", new=mock_sdk_query(empty_response)):
        with patch("claude_agent_sdk.ClaudeAgentOptions"):
            with patch("claude_agent_sdk.AssistantMessage", MagicMock):
                with patch("claude_agent_sdk.TextBlock", MagicMock):
                    with pytest.raises(ValueError, match="No departments found"):
                        await agent.discover_structure("https://example.edu")


def test_validate_department_structure_success(agent):
    """Test validation passes with good data."""
    departments = [
        Department(name="CS", url="https://cs.edu", school="Engineering"),
        Department(name="Math", url="https://math.edu", school="Sciences"),
    ]

    result = agent.validate_department_structure(departments)

    assert result.is_valid
    assert result.total_departments == 2
    assert result.departments_with_urls == 2
    assert result.departments_with_schools == 2


def test_validate_department_structure_no_departments(agent):
    """Test validation fails with no departments."""
    result = agent.validate_department_structure([])

    assert not result.is_valid
    assert "No departments discovered" in result.errors


def test_validate_department_structure_below_threshold(agent):
    """Test validation fails below 50% threshold."""
    departments = [
        Department(name="CS", url="https://cs.edu", school="Engineering"),
        Department(name="Math", url="", school=None),  # Missing url and school
        Department(name="Physics", url="", school=None),  # Missing url and school
    ]

    result = agent.validate_department_structure(departments)

    assert not result.is_valid
    assert len(result.errors) > 0


def test_validate_department_structure_warnings(agent):
    """Test validation passes with warnings between 50-100%."""
    departments = [
        Department(name="CS", url="https://cs.edu", school="Engineering"),
        Department(name="Math", url="https://math.edu", school="Engineering"),
        Department(name="Physics", url="https://phys.edu", school=None),  # 66% have schools
    ]

    result = agent.validate_department_structure(departments)

    assert result.is_valid
    assert result.has_warnings
    assert len(result.warnings) > 0


def test_generate_structure_gap_report(agent, tmp_path):
    """Test gap report generation."""
    departments = [
        Department(name="CS", url="https://cs.edu", school="Engineering"),
        Department(name="Math", url="", school=None),
    ]
    departments[1].add_quality_flag("missing_url")
    departments[1].add_quality_flag("missing_school")

    agent.generate_structure_gap_report(departments)

    report_path = tmp_path / "structure-gaps.md"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "Math" in content
    assert "missing_url" in content
    assert "missing_school" in content


def test_load_manual_fallback_success(agent, tmp_path):
    """Test loading departments from manual fallback."""
    fallback_path = tmp_path / "fallback.json"
    fallback_data = {
        "departments": [
            {
                "name": "Computer Science",
                "url": "https://example.edu/cs",
                "school": "Engineering",
                "hierarchy_level": 1,
            },
            {
                "name": "Mathematics",
                "url": "https://example.edu/math",
                "school": "Sciences",
                "hierarchy_level": 1,
            },
        ]
    }
    with open(fallback_path, "w") as f:
        json.dump(fallback_data, f)

    departments = agent._load_manual_fallback(fallback_path)

    assert len(departments) == 2
    assert all("manual_entry" in d.data_quality_flags for d in departments)
    assert departments[0].name == "Computer Science"
    assert departments[1].name == "Mathematics"


def test_load_manual_fallback_file_not_found(agent, tmp_path):
    """Test loading fallback when file doesn't exist."""
    fallback_path = tmp_path / "nonexistent.json"

    departments = agent._load_manual_fallback(fallback_path)

    assert departments == []


@pytest.mark.asyncio
async def test_run_discovery_workflow(agent, tmp_path, mock_sdk_response):
    """Test complete discovery workflow with checkpointing."""
    system_params = {
        "batch_config": {"department_discovery_batch_size": 5}
    }

    # Mock SDK and agent's discover_structure to return valid departments
    with patch("claude_agent_sdk.query", new=mock_sdk_query(mock_sdk_response)):
        with patch("claude_agent_sdk.ClaudeAgentOptions"):
            with patch("claude_agent_sdk.AssistantMessage", MagicMock):
                with patch("claude_agent_sdk.TextBlock", MagicMock):
                    departments = await agent.run_discovery_workflow(
                        "https://example.edu",
                        system_params=system_params,
                        use_progress_tracker=False,  # Disable for testing
                    )

                    assert len(departments) >= 1

                    # Verify checkpoint was saved
                    checkpoint_files = list(tmp_path.glob("phase-1-departments*.jsonl"))
                    assert len(checkpoint_files) > 0

                    # Verify validation results
                    validation_file = tmp_path / "structure-validation.json"
                    assert validation_file.exists()

                    # Verify gap report
                    gap_report = tmp_path / "structure-gaps.md"
                    assert gap_report.exists()


def test_department_data_quality_flags(agent):
    """Test data quality flags are correctly added."""
    dept = Department(name="CS", url="")
    dept.add_quality_flag("missing_url")

    assert "missing_url" in dept.data_quality_flags
    assert dept.has_quality_issues()

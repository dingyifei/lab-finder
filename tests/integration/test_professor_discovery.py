"""Integration tests for professor discovery agent."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.professor_filter import (
    DomainRateLimiter,
    deduplicate_professors,
    discover_and_save_professors,
    discover_professors_for_department,
    discover_professors_parallel,
    discover_with_playwright_fallback,
    generate_professor_id,
    load_relevant_departments,
    merge_professor_records,
    parse_professor_data,
)
from src.models.department import Department
from src.models.professor import Professor


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

    professors = await discover_professors_for_department(dept, "test-corr-id")
    assert professors == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discover_professors_sdk_failure_triggers_playwright(mocker):
    """Test that WebFetch failure triggers Playwright fallback."""
    # Mock ClaudeSDKClient to raise exception
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(side_effect=Exception("WebFetch failed"))
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


# ===========================================
# Story 3.1b: Parallel Processing Tests
# ===========================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_discovery_with_multiple_departments(mocker):
    """Test parallel execution with asyncio.gather."""

    # Mock discover_professors_for_department
    async def mock_discover(dept, corr_id):
        return [
            Professor(
                id=f"prof-{dept.id}",
                name=f"Prof from {dept.name}",
                title="Professor",
                department_id=dept.id,
                department_name=dept.name,
                profile_url="https://test.edu/faculty/prof",
            )
        ]

    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        side_effect=mock_discover,
    )

    depts = [
        Department(
            id=f"d{i}", name=f"Dept{i}", url=f"http://d{i}.edu", is_relevant=True
        )
        for i in range(5)
    ]
    professors = await discover_professors_parallel(depts, max_concurrent=3)

    assert len(professors) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_semaphore_limits_concurrent_execution(mocker):
    """Test concurrency control with Semaphore."""
    # Track concurrent executions
    active_count = 0
    max_active = 0
    lock = asyncio.Lock()

    async def mock_discover_with_tracking(dept, corr_id):
        nonlocal active_count, max_active

        async with lock:
            active_count += 1
            max_active = max(max_active, active_count)

        await asyncio.sleep(0.1)  # Simulate work

        async with lock:
            active_count -= 1

        return []

    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        side_effect=mock_discover_with_tracking,
    )

    depts = [
        Department(
            id=f"d{i}", name=f"Dept{i}", url=f"http://d{i}.edu", is_relevant=True
        )
        for i in range(10)
    ]
    await discover_professors_parallel(depts, max_concurrent=3)

    # Verify semaphore limited concurrency to 3
    assert max_active <= 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_progress_tracking_updates(mocker):
    """Test progress tracking updates."""
    mock_tracker_instance = MagicMock()
    mocker.patch(
        "src.utils.progress_tracker.ProgressTracker",
        return_value=mock_tracker_instance,
    )

    # Mock discover to return empty lists
    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        return_value=[],
    )

    depts = [
        Department(id=f"d{i}", name=f"Dept{i}", url="test", is_relevant=True)
        for i in range(5)
    ]
    await discover_professors_parallel(depts, max_concurrent=2)

    # Verify progress tracker called
    mock_tracker_instance.start_phase.assert_called_once()
    assert mock_tracker_instance.update.call_count == 5
    mock_tracker_instance.complete_phase.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_failed_department_doesnt_stop_processing(mocker):
    """Test error handling for failed departments."""

    # Mock to fail on 2nd department
    async def mock_discover_with_failure(dept, corr_id):
        if dept.id == "d1":
            raise Exception("Department 1 failed")
        return [
            Professor(
                id=f"prof-{dept.id}",
                name="Prof",
                title="Professor",
                department_id=dept.id,
                department_name=dept.name,
                profile_url="test",
            )
        ]

    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        side_effect=mock_discover_with_failure,
    )

    depts = [
        Department(id=f"d{i}", name=f"Dept{i}", url="test", is_relevant=True)
        for i in range(3)
    ]
    professors = await discover_professors_parallel(depts, max_concurrent=2)

    # Should get professors from d0 and d2, but not d1
    assert len(professors) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_empty_department_list(mocker):
    """Test edge case: Empty department list."""
    mocker.patch("src.agents.professor_filter.discover_professors_for_department")

    professors = await discover_professors_parallel([], max_concurrent=3)

    # Should return empty list without errors
    assert professors == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_departments_fail(mocker):
    """Test edge case: All departments fail."""

    async def mock_discover_always_fail(dept, corr_id):
        raise Exception("All departments failed")

    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        side_effect=mock_discover_always_fail,
    )

    depts = [
        Department(id=f"d{i}", name=f"Dept{i}", url="test", is_relevant=True)
        for i in range(3)
    ]
    professors = await discover_professors_parallel(depts, max_concurrent=2)

    # Should return empty list, not crash
    assert professors == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_single_department(mocker):
    """Test edge case: Single department."""

    async def mock_discover(dept, corr_id):
        return [
            Professor(
                id="prof-1",
                name="Prof Smith",
                title="Professor",
                department_id=dept.id,
                department_name=dept.name,
                profile_url="test",
            )
        ]

    mocker.patch(
        "src.agents.professor_filter.discover_professors_for_department",
        side_effect=mock_discover,
    )

    depts = [Department(id="d1", name="Dept1", url="test", is_relevant=True)]
    professors = await discover_professors_parallel(depts, max_concurrent=5)

    # Should handle single department correctly
    assert len(professors) == 1


# ===========================================
# Story 3.1c: Deduplication, Rate Limiting, and Checkpointing Tests
# ===========================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deduplication_fuzzy_matching(mocker):
    """Test deduplication with LLM-based fuzzy name matching.

    Story 3.1c: Test #1
    """
    # Mock llm_helpers.match_names to return dict with correct lowercase "yes"
    mocker.patch(
        "src.agents.professor_filter.match_names",
        return_value={"decision": "yes", "confidence": 95, "reasoning": "Same person"},
    )

    professors = [
        Professor(
            id="p1",
            name="Dr. Jane Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test1",
        ),
        Professor(
            id="p2",
            name="Jane A. Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test2",
        ),
    ]

    unique = await deduplicate_professors(professors)

    # Should merge to 1 professor (decision="yes" AND confidence >= 90)
    assert len(unique) == 1
    assert unique[0].name in ["Dr. Jane Smith", "Jane A. Smith"]  # Merged record


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limiting_delays_requests():
    """Test that rate limiting enforces delays between requests.

    Story 3.1c: Test #2
    """
    import time

    rate_limiter = DomainRateLimiter(default_rate=2.0, time_period=1.0)  # 2 per second

    start = time.time()

    # Make 5 requests to same domain
    for i in range(5):
        await rate_limiter.acquire("https://example.edu/dept")

    duration = time.time() - start

    # Should take at least 1.4 seconds for 5 requests at 2/sec
    # (First 2 instant, then 3 more at 0.5s intervals = 1.5s total)
    # Allow small margin for timing precision
    assert duration >= 1.4


@pytest.mark.integration
def test_save_professors_checkpoint(tmp_path, mocker):
    """Test saving professors to checkpoint in JSONL format.

    Story 3.1c: Test #3
    """
    from src.utils.checkpoint_manager import CheckpointManager

    checkpoint_manager = CheckpointManager(checkpoint_dir=str(tmp_path))
    professors = [
        Professor(
            id="p1",
            name="Jane",
            title="Prof",
            department_id="d1",
            department_name="CS",
            profile_url="test",
        )
    ]

    checkpoint_manager.save_batch(
        phase="phase-2-professors", batch_id=1, data=professors
    )

    # Verify JSONL file created
    checkpoint_file = tmp_path / "phase-2-professors-batch-1.jsonl"
    assert checkpoint_file.exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_exact_duplicate_skips_llm(mocker):
    """Test that exact duplicates skip LLM calls for efficiency.

    Story 3.1c: Test #4
    """
    # Mock match_names - should NOT be called for exact duplicates
    mock_match = mocker.patch("src.agents.professor_filter.match_names")

    professors = [
        Professor(
            id="p1",
            name="Jane Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test",
        ),
        Professor(
            id="p2",
            name="Jane Smith",  # Exact duplicate
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test",
        ),
    ]

    unique = await deduplicate_professors(professors)

    # Should detect exact duplicate without calling LLM
    mock_match.assert_not_called()
    assert len(unique) == 1


@pytest.mark.integration
def test_merge_professor_records():
    """Test merging professor records prefers more complete data.

    Story 3.1c: Test #5
    """
    existing = Professor(
        id="p1",
        name="Jane",
        title="Prof",
        department_id="d1",
        department_name="CS",
        profile_url="test",
        email=None,
        research_areas=[],
    )
    new = Professor(
        id="p2",
        name="Jane",
        title="Prof",
        department_id="d1",
        department_name="CS",
        profile_url="test",
        email="jane@edu",
        research_areas=["AI", "ML"],
    )

    merged = merge_professor_records(existing, new)

    # Should take email and research_areas from new
    assert merged.email == "jane@edu"
    assert "AI" in merged.research_areas


@pytest.mark.integration
@pytest.mark.asyncio
async def test_high_confidence_no_match_not_treated_as_duplicate(mocker):
    """Verify high-confidence 'no' decisions don't cause incorrect merges.

    Story 3.1c: Test #6 (Critical Edge Case)
    """
    # Mock: High confidence that these are DIFFERENT people
    mocker.patch(
        "src.agents.professor_filter.match_names",
        return_value={
            "decision": "no",
            "confidence": 95,
            "reasoning": "Different people with similar names",
        },
    )

    professors = [
        Professor(
            id="p1",
            name="Jane Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test1",
        ),
        Professor(
            id="p2",
            name="Jane A. Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test2",
        ),
    ]

    unique = await deduplicate_professors(professors)

    # Should NOT merge despite high confidence (because decision is "no")
    assert len(unique) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_discover_and_save_professors_orchestrator(mocker, tmp_path):
    """Test the complete orchestrator workflow.

    Story 3.1c: Integration test for discover_and_save_professors
    """
    # Mock discover_professors_parallel
    mock_professors = [
        Professor(
            id="p1",
            name="Jane Smith",
            department_id="d1",
            department_name="CS",
            title="Professor",
            profile_url="test1",
        ),
        Professor(
            id="p2",
            name="John Doe",
            department_id="d2",
            department_name="Biology",
            title="Professor",
            profile_url="test2",
        ),
    ]
    mocker.patch(
        "src.agents.professor_filter.discover_professors_parallel",
        return_value=mock_professors,
    )

    # Mock deduplicate_professors
    mocker.patch(
        "src.agents.professor_filter.deduplicate_professors",
        return_value=mock_professors,
    )

    # Mock CheckpointManager
    mock_checkpoint_manager = MagicMock()
    mocker.patch(
        "src.agents.professor_filter.CheckpointManager",
        return_value=mock_checkpoint_manager,
    )

    depts = [
        Department(id="d1", name="CS", url="https://cs.edu", is_relevant=True),
        Department(id="d2", name="Biology", url="https://bio.edu", is_relevant=True),
    ]

    result = await discover_and_save_professors(departments=depts, batch_id=1)

    # Verify all steps executed
    assert len(result) == 2
    mock_checkpoint_manager.save_batch.assert_called_once_with(
        phase="phase-2-professors", batch_id=1, data=mock_professors
    )

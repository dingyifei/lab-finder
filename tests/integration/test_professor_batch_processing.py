"""Integration tests for Story 3.5: Batch Processing for Professor Analysis.

Tests batch processing functionality including:
- Parallel LLM calls within batches with semaphore rate limiting
- Batch-level checkpointing and resumability
- Two-level progress tracking
- Failure handling (individual professors and batch infrastructure)
"""

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from src.agents.professor_filtering import (
    filter_professor_batch_parallel,
    filter_professors,
)
from src.models.professor import Professor


@pytest.fixture
def sample_professors() -> list[Professor]:
    """Create sample professors for testing."""
    return [
        Professor(
            id=f"prof-{i}",
            name=f"Prof {i}",
            title="Professor",
            department_id="dept-1",
            department_name="Computer Science",
            research_areas=["AI", "Machine Learning"],
            profile_url=f"https://prof{i}.edu",
            data_quality_flags=[],
        )
        for i in range(20)
    ]


@pytest.fixture
def profile_dict() -> dict[str, str]:
    """User profile dict for testing."""
    return {
        "research_interests": "Machine Learning and AI",
        "current_degree": "PhD in Computer Science",
    }


# ============================================================================
# Test 1: Batch Division with Different Batch Sizes
# ============================================================================


def test_batch_division_different_sizes(sample_professors: list[Professor]) -> None:
    """Test batch division with various batch sizes.

    Story 3.5 AC1: Professor list divided into batches based on config
    """
    # Test small batch size
    batch_size_5 = 5
    total_batches_5 = (len(sample_professors) + batch_size_5 - 1) // batch_size_5
    assert total_batches_5 == 4  # 20 professors / 5 = 4 batches

    # Test medium batch size
    batch_size_10 = 10
    total_batches_10 = (len(sample_professors) + batch_size_10 - 1) // batch_size_10
    assert total_batches_10 == 2  # 20 professors / 10 = 2 batches

    # Test large batch size (larger than list)
    batch_size_30 = 30
    total_batches_30 = (len(sample_professors) + batch_size_30 - 1) // batch_size_30
    assert total_batches_30 == 1  # 20 professors / 30 = 1 batch


# ============================================================================
# Test 2: Async LLM Calls Within Batch
# ============================================================================


@pytest.mark.asyncio
async def test_async_llm_calls_within_batch(
    sample_professors: list[Professor], profile_dict: dict[str, str]
) -> None:
    """Test parallel LLM calls within batch complete faster than sequential.

    Story 3.5 Task 7: Parallel processing within batch
    """
    batch = sample_professors[:10]  # 10 professors
    correlation_id = "test-batch-async"
    max_concurrent = 5

    # Mock LLM call with 0.5 second delay
    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        await asyncio.sleep(0.1)  # Simulate LLM call
        return {
            "decision": "include",
            "confidence": 85,
            "reasoning": "Test match",
            "flags": [],
        }

    with patch(
        "src.agents.professor_filtering.filter_professor_single",
        side_effect=mock_filter_professor_single,
    ):
        start_time = time.time()
        filtered = await filter_professor_batch_parallel(
            batch=batch,
            profile_dict=profile_dict,
            correlation_id=correlation_id,
            max_concurrent=max_concurrent,
        )
        duration = time.time() - start_time

    # Verify results
    assert len(filtered) == 10
    assert all(p.is_relevant for p in filtered)
    assert all(p.relevance_confidence == 85 for p in filtered)

    # Parallel should complete much faster than sequential (10 * 0.1 = 1.0s)
    # With semaphore=5, should take ~0.2s (2 waves of 5)
    assert duration < 0.5  # Generous upper bound


# ============================================================================
# Test 3: Batch Checkpoint Creation
# ============================================================================


@pytest.mark.asyncio
async def test_batch_checkpoint_creation(
    tmp_path: Path, sample_professors: list[Professor], profile_dict: dict[str, str]
) -> None:
    """Test batch checkpoint files are created after each batch.

    Story 3.5 AC3: Checkpoint saved after each batch completion
    """
    batch = sample_professors[:5]
    correlation_id = "test-checkpoint"

    # Mock LLM and checkpoint manager
    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        return {
            "decision": "include",
            "confidence": 90,
            "reasoning": "Match",
            "flags": [],
        }

    mock_checkpoint_manager = Mock()
    mock_checkpoint_manager.save_batch = Mock()

    with (
        patch(
            "src.agents.professor_filtering.filter_professor_single",
            side_effect=mock_filter_professor_single,
        ),
        patch(
            "src.agents.professor_filtering.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
    ):
        filtered = await filter_professor_batch_parallel(
            batch=batch,
            profile_dict=profile_dict,
            correlation_id=correlation_id,
            max_concurrent=3,
        )

    # Verify filtered batch
    assert len(filtered) == 5
    assert all(p.is_relevant for p in filtered)


# ============================================================================
# Test 4: Resume from Checkpoint (Partial Completion)
# ============================================================================


@pytest.mark.asyncio
async def test_resume_from_checkpoint(
    tmp_path: Path, sample_professors: list[Professor]
) -> None:
    """Test resumability from last completed batch.

    Story 3.5 AC5: If execution interrupted, resumable from last completed batch
    """
    # Mock checkpoint manager with resume point = 2 (already completed batches 0, 1)
    mock_checkpoint_manager = Mock()
    mock_checkpoint_manager.get_resume_point = Mock(return_value=2)
    mock_checkpoint_manager.load_batches = Mock(return_value=[])
    mock_checkpoint_manager.save_batch = Mock()

    # Mock user profile loading
    mock_profile = {"research_interests": "ML", "current_degree": "PhD"}

    # Mock filter_professor_single to track which professors are processed
    processed_professors = []

    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        processed_professors.append(professor.id)
        return {
            "decision": "include",
            "confidence": 80,
            "reasoning": "Match",
            "flags": [],
        }

    # Mock SystemParams
    mock_system_params = Mock()
    mock_system_params.batch_config.professor_filtering_batch_size = 5
    mock_system_params.rate_limiting.max_concurrent_llm_calls = 3
    mock_system_params.confidence_thresholds.professor_filter = 70.0
    mock_system_params.filtering_config.low_confidence_threshold = 70
    mock_system_params.filtering_config.high_confidence_threshold = 90

    with (
        patch(
            "src.agents.professor_filtering.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch(
            "src.agents.professor_filtering.load_user_profile",
            return_value=mock_profile,
        ),
        patch(
            "src.agents.professor_filtering.filter_professor_single",
            side_effect=mock_filter_professor_single,
        ),
        patch(
            "src.agents.professor_filtering.SystemParams.load",
            return_value=mock_system_params,
        ),
        patch("src.agents.professor_filtering.ProgressTracker"),
        patch("src.utils.confidence.apply_manual_overrides", return_value=0),
        patch(
            "src.utils.confidence.calculate_confidence_stats",
            return_value={
                "total_professors": 20,
                "included": {"high": 20, "medium": 0, "low": 0},
                "excluded": {"high": 0, "medium": 0, "low": 0},
                "distribution_analysis": {"quality_assessment": "Good"},
            },
        ),
        patch("src.utils.confidence.save_confidence_stats_report"),
    ):
        # Mock load_batches to return all professors as if from discovery phase
        mock_checkpoint_manager.load_batches.return_value = [
            p.model_dump() for p in sample_professors
        ]

        await filter_professors("test-resume")

    # Verify checkpoint manager was called correctly
    mock_checkpoint_manager.get_resume_point.assert_called_once_with("phase-2-filter")

    # Verify save_batch was called for batches 2, 3 (batch_size=5, so 4 total batches, resume from 2)
    # Total batches = ceil(20/5) = 4, resume from batch 2, so process batches 2, 3 (0-indexed)
    assert mock_checkpoint_manager.save_batch.call_count == 2

    # Verify only professors from batches 2-3 were processed (10 professors)
    assert len(processed_professors) == 10


# ============================================================================
# Test 5: Progress Tracking for Batches
# ============================================================================


@pytest.mark.asyncio
async def test_progress_tracking_batches(
    sample_professors: list[Professor], profile_dict: dict[str, str]
) -> None:
    """Test two-level progress tracking (batch-level and within-batch).

    Story 3.5 AC4: Progress indicators show batch X of Y
    Story 3.5 Task 6: Two-level progress tracking
    """
    # Mock progress tracker
    mock_tracker = Mock()
    mock_tracker.start_phase = Mock()
    mock_tracker.update_batch = Mock()
    mock_tracker.update = Mock()
    mock_tracker.complete_phase = Mock()

    # Mock user profile
    mock_profile = {"research_interests": "ML", "current_degree": "PhD"}

    # Mock filter_professor_single
    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        return {
            "decision": "include",
            "confidence": 85,
            "reasoning": "Match",
            "flags": [],
        }

    # Mock checkpoint manager
    mock_checkpoint_manager = Mock()
    mock_checkpoint_manager.get_resume_point = Mock(return_value=0)
    mock_checkpoint_manager.load_batches = Mock(
        return_value=[p.model_dump() for p in sample_professors]
    )
    mock_checkpoint_manager.save_batch = Mock()

    # Mock SystemParams
    mock_system_params = Mock()
    mock_system_params.batch_config.professor_filtering_batch_size = 5
    mock_system_params.rate_limiting.max_concurrent_llm_calls = 3
    mock_system_params.confidence_thresholds.professor_filter = 70.0
    mock_system_params.filtering_config.low_confidence_threshold = 70
    mock_system_params.filtering_config.high_confidence_threshold = 90

    with (
        patch(
            "src.agents.professor_filtering.ProgressTracker", return_value=mock_tracker
        ),
        patch(
            "src.agents.professor_filtering.load_user_profile",
            return_value=mock_profile,
        ),
        patch(
            "src.agents.professor_filtering.filter_professor_single",
            side_effect=mock_filter_professor_single,
        ),
        patch(
            "src.agents.professor_filtering.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch(
            "src.agents.professor_filtering.SystemParams.load",
            return_value=mock_system_params,
        ),
        patch("src.utils.confidence.apply_manual_overrides", return_value=0),
        patch(
            "src.utils.confidence.calculate_confidence_stats",
            return_value={
                "total_professors": 20,
                "included": {"high": 20, "medium": 0, "low": 0},
                "excluded": {"high": 0, "medium": 0, "low": 0},
                "distribution_analysis": {"quality_assessment": "Good"},
            },
        ),
        patch("src.utils.confidence.save_confidence_stats_report"),
    ):
        await filter_professors("test-progress")

    # Verify progress tracking calls
    mock_tracker.start_phase.assert_called_once()
    assert mock_tracker.update_batch.call_count == 4  # 4 batches (20/5)
    assert mock_tracker.update.call_count >= 4  # At least 4 updates (one per batch)
    mock_tracker.complete_phase.assert_called_once()


# ============================================================================
# Test 6: Batch Processing Failure Handling
# ============================================================================


@pytest.mark.asyncio
async def test_individual_professor_failure_handling(
    sample_professors: list[Professor], profile_dict: dict[str, str]
) -> None:
    """Test individual professor LLM failures within batch.

    Story 3.5 Task 8: Individual professor failures use inclusive fallback
    """
    batch = sample_professors[:5]
    correlation_id = "test-failure"

    # Mock filter_professor_single to fail for some professors
    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        if "prof-1" in professor.id or "prof-3" in professor.id:
            raise Exception("LLM API timeout")
        return {
            "decision": "include",
            "confidence": 90,
            "reasoning": "Match",
            "flags": [],
        }

    with patch(
        "src.agents.professor_filtering.filter_professor_single",
        side_effect=mock_filter_professor_single,
    ):
        filtered = await filter_professor_batch_parallel(
            batch=batch,
            profile_dict=profile_dict,
            correlation_id=correlation_id,
            max_concurrent=3,
        )

    # Verify all professors returned (no batch failure)
    assert len(filtered) == 5

    # Verify failed professors have inclusive fallback
    failed_profs = [
        p for p in filtered if "llm_filtering_failed" in p.data_quality_flags
    ]
    assert len(failed_profs) == 2  # prof-1 and prof-3

    # Verify failed professors marked as relevant (inclusive)
    for prof in failed_profs:
        assert prof.is_relevant is True
        assert prof.relevance_confidence == 0
        assert "Filter error:" in prof.relevance_reasoning


@pytest.mark.asyncio
async def test_batch_infrastructure_failure(sample_professors: list[Professor]) -> None:
    """Test batch infrastructure failure re-raises exception.

    Story 3.5 Task 8: Infrastructure failures re-raise for resumability
    """
    # Mock checkpoint manager to fail on save_batch
    mock_checkpoint_manager = Mock()
    mock_checkpoint_manager.get_resume_point = Mock(return_value=0)
    mock_checkpoint_manager.load_batches = Mock(
        return_value=[p.model_dump() for p in sample_professors[:5]]
    )
    mock_checkpoint_manager.save_batch = Mock(
        side_effect=Exception("Disk full - checkpoint write failed")
    )

    # Mock user profile
    mock_profile = {"research_interests": "ML", "current_degree": "PhD"}

    # Mock filter_professor_single
    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        return {
            "decision": "include",
            "confidence": 85,
            "reasoning": "Match",
            "flags": [],
        }

    # Mock SystemParams
    mock_system_params = Mock()
    mock_system_params.batch_config.professor_filtering_batch_size = 5
    mock_system_params.rate_limiting.max_concurrent_llm_calls = 3
    mock_system_params.confidence_thresholds.professor_filter = 70.0
    mock_system_params.filtering_config.low_confidence_threshold = 70
    mock_system_params.filtering_config.high_confidence_threshold = 90

    with (
        patch(
            "src.agents.professor_filtering.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch(
            "src.agents.professor_filtering.load_user_profile",
            return_value=mock_profile,
        ),
        patch(
            "src.agents.professor_filtering.filter_professor_single",
            side_effect=mock_filter_professor_single,
        ),
        patch(
            "src.agents.professor_filtering.SystemParams.load",
            return_value=mock_system_params,
        ),
        patch("src.agents.professor_filtering.ProgressTracker"),
    ):
        # Verify exception is re-raised (not caught)
        with pytest.raises(Exception, match="Disk full"):
            await filter_professors("test-infrastructure-failure")


# ============================================================================
# Test 7: Integration Test with Full Batch Processing Flow
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_batch_processing_flow(sample_professors: list[Professor]) -> None:
    """Integration test for complete batch processing workflow.

    Tests end-to-end:
    - Load config
    - Divide into batches
    - Process batches sequentially
    - Parallel LLM calls within batch
    - Save checkpoints
    - Progress tracking
    - Generate reports
    """
    # Mock all dependencies
    mock_checkpoint_manager = Mock()
    mock_checkpoint_manager.get_resume_point = Mock(return_value=0)
    mock_checkpoint_manager.load_batches = Mock(
        return_value=[p.model_dump() for p in sample_professors]
    )
    mock_checkpoint_manager.save_batch = Mock()

    mock_profile = {"research_interests": "ML and AI", "current_degree": "PhD"}

    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        # Vary confidence to test distribution
        confidence = 95 if int(professor.id.split("-")[1]) % 2 == 0 else 85
        return {
            "decision": "include",
            "confidence": confidence,
            "reasoning": "Research match",
            "flags": [],
        }

    mock_system_params = Mock()
    mock_system_params.batch_config.professor_filtering_batch_size = 10
    mock_system_params.rate_limiting.max_concurrent_llm_calls = 5
    mock_system_params.confidence_thresholds.professor_filter = 70.0
    mock_system_params.filtering_config.low_confidence_threshold = 70
    mock_system_params.filtering_config.high_confidence_threshold = 90

    with (
        patch(
            "src.agents.professor_filtering.CheckpointManager",
            return_value=mock_checkpoint_manager,
        ),
        patch(
            "src.agents.professor_filtering.load_user_profile",
            return_value=mock_profile,
        ),
        patch(
            "src.agents.professor_filtering.filter_professor_single",
            side_effect=mock_filter_professor_single,
        ),
        patch(
            "src.agents.professor_filtering.SystemParams.load",
            return_value=mock_system_params,
        ),
        patch("src.agents.professor_filtering.ProgressTracker"),
        patch("src.utils.confidence.apply_manual_overrides", return_value=0),
        patch(
            "src.utils.confidence.calculate_confidence_stats",
            return_value={
                "total_professors": 20,
                "included": {"high": 10, "medium": 10, "low": 0},
                "excluded": {"high": 0, "medium": 0, "low": 0},
                "distribution_analysis": {"quality_assessment": "Good"},
            },
        ),
        patch("src.utils.confidence.save_confidence_stats_report"),
    ):
        result = await filter_professors("test-integration")

    # Verify results
    assert len(result) == 20
    assert all(p.is_relevant for p in result)  # All matched threshold

    # Verify checkpoints saved (2 batches: 20/10)
    assert mock_checkpoint_manager.save_batch.call_count == 2

    # Verify save_batch called with correct phase and batch IDs
    calls = mock_checkpoint_manager.save_batch.call_args_list
    assert calls[0][1]["phase"] == "phase-2-filter"
    assert calls[0][1]["batch_id"] == 1
    assert calls[1][1]["batch_id"] == 2


# ============================================================================
# Test 8: Rate Limiting Enforcement (Semaphore Limits Concurrent LLM Calls)
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limiting_semaphore(
    sample_professors: list[Professor], profile_dict: dict[str, str]
) -> None:
    """Test semaphore limits concurrent LLM calls.

    Story 3.5 Task 7: Semaphore enforces max_concurrent_llm_calls limit
    """
    batch = sample_professors[:15]  # 15 professors
    correlation_id = "test-rate-limit"
    max_concurrent = 3  # Strict limit

    # Track concurrent calls
    concurrent_calls = []
    max_concurrent_observed = 0

    async def mock_filter_professor_single(
        professor: Professor, profile: dict[str, str], corr_id: str
    ) -> dict[str, Any]:
        nonlocal max_concurrent_observed
        concurrent_calls.append(1)
        current_concurrent = len(concurrent_calls)
        max_concurrent_observed = max(max_concurrent_observed, current_concurrent)

        await asyncio.sleep(0.05)  # Simulate work

        concurrent_calls.pop()
        return {
            "decision": "include",
            "confidence": 90,
            "reasoning": "Match",
            "flags": [],
        }

    with patch(
        "src.agents.professor_filtering.filter_professor_single",
        side_effect=mock_filter_professor_single,
    ):
        filtered = await filter_professor_batch_parallel(
            batch=batch,
            profile_dict=profile_dict,
            correlation_id=correlation_id,
            max_concurrent=max_concurrent,
        )

    # Verify semaphore limit enforced
    assert len(filtered) == 15
    assert max_concurrent_observed <= max_concurrent  # Never exceeded limit
    assert max_concurrent_observed >= 2  # Actually used concurrency

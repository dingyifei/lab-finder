"""Test sub-agent spawning with AgentDefinition pattern.

Sprint Change Proposal: SCP-2025-10-11 Phase 1 Day 2-3
Tests the sub-agent spawning implementation using AgentDefinition.
"""

import asyncio
import sys
import pytest
from src.utils.agentic_patterns import spawn_sub_agent, parallel_sub_agents


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spawn_sub_agent_basic():
    """Test basic sub-agent spawning with simple task using template-based agents."""
    result = await spawn_sub_agent(
        agent_name="data-extractor",
        task_prompt="Extract the main text content from https://example.com",
        correlation_id="test-sub-agent-basic",
        timeout=40,
    )

    # Should return a result dict
    assert "data" in result
    assert "success" in result
    assert "error" in result

    # Error should be None if successful, or set if failed
    # (example.com might not return structured data, so success could be False)
    print(f"\nSub-agent result: {result}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spawn_sub_agent_with_format():
    """Test sub-agent with structured output requirement using template-based agents."""
    result = await spawn_sub_agent(
        agent_name="data-extractor",
        task_prompt="""Extract data from https://example.com and return as JSON:
        {
            "title": "page title",
            "content": "main content summary"
        }""",
        correlation_id="test-sub-agent-format",
        timeout=40,
    )

    assert "data" in result
    assert "success" in result

    # If successful, data should be a dict or list
    if result["success"]:
        assert isinstance(result["data"], (dict, list))

    print(f"\nSub-agent structured result: {result}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spawn_sub_agent_error_handling():
    """Test sub-agent error handling with invalid URL.

    Note: spawn_sub_agent now has built-in 30s timeout to prevent hanging.
    The function will gracefully return an error dict on timeout.
    """
    # spawn_sub_agent has built-in timeout protection
    result = await spawn_sub_agent(
        agent_name="data-extractor",
        task_prompt="Extract content from https://this-url-definitely-does-not-exist-12345.com",
        correlation_id="test-sub-agent-error",
        timeout=40,  # Internal timeout handles SDK hangs
    )

    # Should return gracefully even on error
    assert "data" in result
    assert "success" in result
    assert "error" in result

    # Likely will fail, but should handle gracefully
    print(f"\nSub-agent error handling result: {result}")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows subprocess IPC limitation - parallel SDK spawning causes deadlock (documented in PHASE-1-POC-HANDOFF.md)"
)
async def test_parallel_sub_agents():
    """Test parallel sub-agent execution with concurrency control using template-based agents.

    Note: Each sub-agent has built-in 30s timeout. With max_concurrent=2,
    this should complete in ~60-90s for 3 tasks.

    Windows: This test is skipped on Windows due to subprocess IPC buffer limitations
    when spawning multiple SDK clients simultaneously. Individual agent spawning works
    perfectly (see other tests). This is a known OS limitation, not an implementation bug.
    """
    tasks = [
        {
            "agent_name": "data-extractor",
            "task_prompt": "Extract title and content from https://example.com as JSON",
            "timeout": 30,
        },
        {
            "agent_name": "data-extractor",
            "task_prompt": "Extract title and content from https://example.org as JSON",
            "timeout": 30,
        },
        {
            "agent_name": "data-extractor",
            "task_prompt": "Extract title and content from https://example.net as JSON",
            "timeout": 30,
        },
    ]

    try:
        results = await asyncio.wait_for(
            parallel_sub_agents(
                tasks,
                max_concurrent=2,  # Limit to 2 concurrent
                correlation_id="test-parallel-sub-agents",
            ),
            timeout=120  # 120s total timeout for all tasks
        )
    except asyncio.TimeoutError:
        pytest.fail("parallel_sub_agents() timed out after 120s")

    # Should return same number of results as tasks
    assert len(results) == len(tasks)

    # Each result should have expected structure
    for result in results:
        assert "data" in result
        assert "success" in result
        assert "error" in result

    # Count successes
    successful = sum(1 for r in results if r["success"])
    print(f"\nParallel sub-agents: {successful}/{len(tasks)} succeeded")


if __name__ == "__main__":
    print("Testing sub-agent spawning...")
    asyncio.run(test_spawn_sub_agent_basic())
    asyncio.run(test_spawn_sub_agent_with_format())
    asyncio.run(test_spawn_sub_agent_error_handling())
    asyncio.run(test_parallel_sub_agents())
    print("\nAll sub-agent tests complete!")

"""Simple test for agentic scraping pattern - Phase 1 Day 4."""

import asyncio
import time

import pytest

from src.utils.agentic_patterns import agentic_discovery_with_tools
from src.utils.logger import get_logger


@pytest.mark.integration
@pytest.mark.slow
async def test_simple_agentic_webfetch():
    """Test agentic pattern with simple web fetch - example.com."""
    logger = get_logger(
        correlation_id="simple-agentic-test",
        phase="poc-validation",
        component="simple-test",
    )

    logger.info("Starting simple agentic web fetch test")

    # System prompt - SHORT role only
    system_prompt = "You are a web scraping assistant."  # 35 chars

    # Initial prompt - SHORT task description
    initial_prompt = "Extract title and main content from https://example.com"  # 63 chars

    # Detailed instructions - Can be LONG
    detailed_instructions = """
<task>
Navigate to https://example.com and extract the following information:
1. Page title (from <title> tag or <h1>)
2. Main heading text
3. Any paragraph content

Use WebFetch to get the page content, then extract the data.
</task>

<approach>
- Use WebFetch tool to fetch the HTML content
- Parse the HTML to find title, headings, and paragraphs
- Return the extracted data in a structured format
</approach>

<quality>
Ensure all extracted text is clean and properly formatted.
</quality>
"""

    # Format template
    format_template = """
{
  "title": "page title here",
  "heading": "main heading here",
  "content": "paragraph content here"
}
"""

    start_time = time.time()

    try:
        result = await agentic_discovery_with_tools(
            prompt=initial_prompt,
            max_turns=5,
            allowed_tools=["WebFetch"],
            system_prompt=system_prompt,
            format_template=format_template,
            detailed_instructions=detailed_instructions,
            correlation_id="simple-agentic-test",
        )

        execution_time = time.time() - start_time

        logger.info(
            "Simple agentic test complete",
            execution_time=execution_time,
            turns_used=result["turns_used"],
            tools_used=result["tools_used"],
            format_valid=result["format_valid"],
        )

        # Print results for visibility
        print(f"\n=== Simple Agentic Test Results ===")
        print(f"Execution Time: {execution_time:.2f}s")
        print(f"Turns Used: {result['turns_used']}")
        print(f"Tools Used: {result['tools_used']}")
        print(f"Format Valid: {result['format_valid']}")
        print(f"Data Extracted: {result['data']}")
        print(f"Conversation Length: {len(result['conversation_log'])} messages")

        # Assertions
        assert result["turns_used"] > 0, "Should use at least 1 turn"
        assert "WebFetch" in result["tools_used"], "Should use WebFetch tool"
        assert result["data"], "Should extract some data"

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "Simple agentic test failed",
            error=str(e),
            execution_time=execution_time,
        )
        raise


@pytest.mark.integration
@pytest.mark.slow
async def test_agentic_with_timeout_and_progress():
    """Test agentic pattern with longer timeout and progress logging."""
    logger = get_logger(
        correlation_id="agentic-progress-test",
        phase="poc-validation",
        component="progress-test",
    )

    logger.info("Starting agentic test with progress tracking")

    system_prompt = "You are a web scraping assistant."
    initial_prompt = "Find information about research professors at https://example.com"

    detailed_instructions = """
<task>
Your goal is to discover professors and their research areas.

Steps:
1. Use WebFetch to fetch the page
2. Look for any faculty listings or academic staff
3. Extract names, titles, and any research information you find

Note: This is example.com so there won't be real professors, but demonstrate the pattern.
</task>
"""

    format_template = """
[
  {
    "name": "Professor Name",
    "title": "Position",
    "research_areas": ["area1", "area2"]
  }
]
"""

    start_time = time.time()

    # Add progress logging
    async def log_progress():
        """Log progress every 10 seconds."""
        elapsed = 0
        while True:
            await asyncio.sleep(10)
            elapsed += 10
            logger.info(f"Still running... {elapsed}s elapsed")

    progress_task = asyncio.create_task(log_progress())

    try:
        result = await asyncio.wait_for(
            agentic_discovery_with_tools(
                prompt=initial_prompt,
                max_turns=5,
                allowed_tools=["WebFetch", "WebSearch"],
                system_prompt=system_prompt,
                format_template=format_template,
                detailed_instructions=detailed_instructions,
                correlation_id="agentic-progress-test",
            ),
            timeout=180.0,  # 3 minutes timeout
        )

        progress_task.cancel()
        execution_time = time.time() - start_time

        logger.info(
            "Agentic test with progress complete",
            execution_time=execution_time,
            turns_used=result["turns_used"],
        )

        print(f"\n=== Agentic Test with Progress Results ===")
        print(f"Execution Time: {execution_time:.2f}s")
        print(f"Turns Used: {result['turns_used']}")
        print(f"Tools Used: {result['tools_used']}")

        assert result["turns_used"] > 0

    except asyncio.TimeoutError:
        progress_task.cancel()
        execution_time = time.time() - start_time
        logger.error("Test timed out", execution_time=execution_time)
        pytest.fail(f"Test timed out after {execution_time:.2f}s")

    except Exception as e:
        progress_task.cancel()
        execution_time = time.time() - start_time
        logger.error("Test failed", error=str(e), execution_time=execution_time)
        raise

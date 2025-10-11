"""Test agentic_discovery_with_tools() function directly."""

import asyncio
from src.utils.agentic_patterns import agentic_discovery_with_tools
from src.utils.logger import get_logger


async def test_agentic_function():
    """Test the actual agentic_discovery_with_tools function."""
    print("=== Testing agentic_discovery_with_tools() ===\n")

    # Add logger setup like in professor_discovery.py
    logger = get_logger(
        correlation_id="test-with-logger",
        phase="test",
        component="test",
    )
    logger.info("Testing with logger setup")

    try:
        result = await agentic_discovery_with_tools(
            prompt="Use WebFetch to get https://example.com and extract the title",
            max_turns=3,
            allowed_tools=["WebFetch", "WebSearch"],
            system_prompt="You are a web scraping assistant.",
            format_template='{"title": "..."}',
            correlation_id="test-agentic-function",
        )

        print("\nSUCCESS!")
        print(f"Turns used: {result['turns_used']}")
        print(f"Tools used: {result['tools_used']}")
        print(f"Format valid: {result['format_valid']}")
        print(f"Data: {result['data']}")

    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing agentic_discovery_with_tools() function...\n")
    asyncio.run(test_agentic_function())

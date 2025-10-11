"""Minimal multi-turn test matching SDK examples exactly.

Based on streaming_mode.py example_multi_turn_conversation()
"""

import asyncio
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)


async def test_multi_turn_simple():
    """Test multi-turn exactly like SDK example."""
    print("=== Multi-Turn Test (SDK Example Pattern) ===\n")

    # Exactly like streaming_mode.py line 78-94
    async with ClaudeSDKClient() as client:
        # First turn
        print("Turn 1: What's the capital of France?")
        await client.query("What's the capital of France?")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 1: {block.text[:100]}")

        # Second turn - follow-up
        print("\nTurn 2: What's the population of that city?")
        await client.query("What's the population of that city?")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 2: {block.text[:100]}")

    print("\nSUCCESS: Multi-turn conversation worked!")


async def test_multi_turn_with_tools():
    """Test multi-turn with WebFetch tool."""
    print("\n=== Multi-Turn With Tools Test ===\n")

    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch"],
        max_turns=3,
    )

    async with ClaudeSDKClient(options=options) as client:
        # First turn
        print("Turn 1: Fetch example.com")
        await client.query("Use WebFetch to get https://example.com")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 1: {block.text[:100]}")

        # Second turn
        print("\nTurn 2: What was the title?")
        await client.query("What was the title of that page?")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 2: {block.text[:100]}")

    print("\nSUCCESS: Multi-turn with tools worked!")


async def test_our_agentic_pattern():
    """Test our agentic pattern in isolation."""
    print("\n=== Our Agentic Pattern Test ===\n")

    options = ClaudeAgentOptions(
        allowed_tools=["WebFetch", "WebSearch"],
        max_turns=3,
        system_prompt="You are a web scraping assistant.",
    )

    print("Initializing ClaudeSDKClient...")
    async with ClaudeSDKClient(options=options) as client:
        print("Client initialized successfully!")

        # Initial query
        print("\nTurn 1: Initial query")
        await client.query("Use WebFetch to get https://example.com and tell me the title")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 1: {block.text[:100]}")

        # Format reinforcement (THIS IS WHERE WE MIGHT FAIL)
        print("\nTurn 2: Format reinforcement")
        await client.query("Format your response as JSON: {\"title\": \"...\"}")

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(f"Response 2: {block.text[:100]}")

    print("\nSUCCESS: Our pattern worked!")


async def main():
    """Run all tests."""
    try:
        await test_multi_turn_simple()
    except Exception as e:
        print(f"\nFAILED test_multi_turn_simple: {e}\n")

    try:
        await test_multi_turn_with_tools()
    except Exception as e:
        print(f"\nFAILED test_multi_turn_with_tools: {e}\n")

    try:
        await test_our_agentic_pattern()
    except Exception as e:
        print(f"\nFAILED test_our_agentic_pattern: {e}\n")


if __name__ == "__main__":
    print("Testing multi-turn conversation patterns...\n")
    asyncio.run(main())

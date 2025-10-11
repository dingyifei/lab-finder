"""Minimal SDK test to isolate initialization issue.

Tests basic ClaudeSDKClient functionality with WebFetch.
"""

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)


async def test_minimal_sdk():
    """Minimal test of SDK initialization and WebFetch."""
    print("="  * 80)
    print("MINIMAL SDK TEST - claude-agent-sdk 0.1.3")
    print("=" * 80)

    claude_dir = Path(__file__).parent / "claude"
    print(f"\nClaude directory: {claude_dir}")
    print(f"Exists: {claude_dir.exists()}")

    # Test 1: Minimal configuration
    print("\n[TEST 1] Minimal configuration (no tools)")
    print("-" * 80)
    try:
        options1 = ClaudeAgentOptions(
            max_turns=1,
            system_prompt="You are a test assistant.",
            cwd=claude_dir,
            setting_sources=None,
        )

        async with ClaudeSDKClient(options=options1) as client:
            await client.query("Say 'Hello World'")
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"SUCCESS: {block.text[:100]}")
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 2: With WebFetch tool
    print("\n[TEST 2] With WebFetch tool")
    print("-" * 80)
    try:
        options2 = ClaudeAgentOptions(
            allowed_tools=["WebFetch"],
            max_turns=1,
            system_prompt="You are a web fetching assistant.",
            cwd=claude_dir,
            setting_sources=None,
        )

        async with ClaudeSDKClient(options=options2) as client:
            await client.query("Use WebFetch to get https://example.com and tell me the title")
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"SUCCESS: {block.text[:200]}")
    except Exception as e:
        print(f"FAILED: {e}")

    # Test 3: With project settings
    print("\n[TEST 3] With project settings (MCP config)")
    print("-" * 80)
    try:
        options3 = ClaudeAgentOptions(
            allowed_tools=["WebFetch"],
            max_turns=1,
            system_prompt="You are a web fetching assistant.",
            cwd=claude_dir,
            setting_sources=["project"],  # Load .mcp.json
        )

        async with ClaudeSDKClient(options=options3) as client:
            await client.query("Use WebFetch to get https://example.com and tell me the title")
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(f"SUCCESS: {block.text[:200]}")
    except Exception as e:
        print(f"FAILED: {e}")

    print("\n" + "=" * 80)
    print("MINIMAL SDK TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    print("\nRunning minimal SDK test to isolate issue...")
    print("This will test SDK 0.1.3 with different configurations\n")
    asyncio.run(test_minimal_sdk())

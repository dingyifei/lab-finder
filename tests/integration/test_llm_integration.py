"""Integration test for LLM helpers with claude_agent_sdk.

This test verifies that call_llm_with_retry() successfully integrates with
the Claude Agent SDK for actual LLM calls.

NOTE: These tests require Claude Code CLI authentication and are skipped in CI.
Run locally with Claude Code signed in to test LLM integration.
"""

import os
import pytest
from src.utils.llm_helpers import call_llm_with_retry


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Requires Claude Code CLI authentication - ClaudeSDKClient uses CLI auth, not ANTHROPIC_API_KEY"
)
async def test_call_llm_with_retry_basic():
    """Test that call_llm_with_retry() successfully calls Claude Agent SDK."""

    # Simple prompt to test LLM integration
    prompt = "What is 2 + 2? Respond with only the number."

    # Call LLM
    response = await call_llm_with_retry(prompt, correlation_id="test-llm-integration")

    # Verify we got a response
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

    # Response should contain the number 4
    assert "4" in response


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Requires Claude Code CLI authentication - ClaudeSDKClient uses CLI auth, not ANTHROPIC_API_KEY"
)
async def test_call_llm_with_retry_json_response():
    """Test that call_llm_with_retry() handles JSON responses correctly."""

    prompt = """Respond with a JSON object containing a greeting.

Format:
{
  "greeting": "Hello, World!"
}
"""

    # Call LLM
    response = await call_llm_with_retry(prompt, correlation_id="test-llm-json")

    # Verify we got a response
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

    # Response should be parseable as JSON or contain JSON
    import json

    # Try to extract JSON from response (may be in code blocks)
    json_text = response.strip()
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    elif json_text.startswith("```"):
        json_text = json_text[3:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]
    json_text = json_text.strip()

    # Should be valid JSON
    parsed = json.loads(json_text)
    assert "greeting" in parsed

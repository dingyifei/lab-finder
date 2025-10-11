"""Agentic Discovery Patterns.

Reusable patterns for multi-turn agentic discovery workflows.

Sprint Change Proposal: SCP-2025-10-11 Agentic Discovery Architecture
Phase 1: POC Implementation

This module provides core patterns for agentic discovery:
- Multi-turn conversation with autonomous tool selection
- Sub-agent spawning via Task tool
- Format reinforcement for structured output
- Self-evaluation and iterative refinement
"""

import json
import re
from typing import Any, Optional

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
)

from src.utils.logger import get_logger


async def agentic_discovery_with_tools(
    prompt: str,
    max_turns: int,
    allowed_tools: list[str],
    system_prompt: str,
    format_template: Optional[str] = None,
    correlation_id: str = "agentic-discovery",
) -> dict[str, Any]:
    """Execute agentic discovery with multi-turn conversation and autonomous tool usage.

    This is the CORE agentic pattern. The agent:
    1. Receives initial task description
    2. Autonomously explores using allowed tools (WebFetch, WebSearch, Puppeteer MCP)
    3. Evaluates own progress and completeness
    4. Continues exploration until satisfied or max_turns reached
    5. Receives format reinforcement on final turn if template provided

    Key differences from zero-shot:
    - Agent makes tool selection decisions (not Python)
    - Multi-turn conversation allows iterative refinement
    - Agent thinks about what data is missing
    - Format reinforcement ensures structured output

    Args:
        prompt: Initial task description for the agent
        max_turns: Maximum conversation turns (3-5 recommended)
        allowed_tools: Tools available to agent (e.g., ["WebFetch", "WebSearch"])
        system_prompt: System prompt defining agent's role
        format_template: Optional JSON format template for final turn
        correlation_id: Correlation ID for logging

    Returns:
        dict with keys:
            - data: Extracted data (dict or list)
            - turns_used: Number of conversation turns
            - tools_used: List of tools the agent used
            - format_valid: Whether output matched expected format
            - raw_response: Final response text

    Raises:
        Exception: If conversation fails or max retries exceeded

    Example:
        >>> result = await agentic_discovery_with_tools(
        ...     prompt="Discover professors at https://cs.example.edu/faculty",
        ...     max_turns=3,
        ...     allowed_tools=["WebFetch", "WebSearch"],
        ...     system_prompt="You are a web scraping assistant...",
        ...     format_template='[{"name": "...", "title": "..."}]'
        ... )
        >>> print(result["data"])  # List of professors
        >>> print(result["turns_used"])  # e.g., 2
        >>> print(result["tools_used"])  # e.g., ["WebFetch"]

    Story: Phase 1 POC - Core agentic pattern
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="agentic_discovery",
        component="agentic_patterns",
    )
    logger.info(
        "Starting agentic discovery",
        max_turns=max_turns,
        allowed_tools=allowed_tools,
        has_format_template=bool(format_template),
    )

    # Configure SDK for agentic mode
    options = ClaudeAgentOptions(
        allowed_tools=allowed_tools,
        max_turns=max_turns,
        system_prompt=system_prompt,
        setting_sources=None,  # Isolated context
    )

    turns_used = 0
    tools_used: list[str] = []
    raw_response = ""
    conversation_log: list[dict[str, str]] = []

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Initial query
            await client.query(prompt)
            turns_used += 1
            conversation_log.append({"role": "user", "content": prompt})

            # Multi-turn conversation loop
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            raw_response = block.text
                            conversation_log.append(
                                {"role": "assistant", "content": block.text}
                            )

                            # Track tool usage (inferred from response)
                            # TODO: Better tool tracking via SDK message types
                            if "WebFetch" in block.text or "fetched" in block.text.lower():
                                if "WebFetch" not in tools_used:
                                    tools_used.append("WebFetch")
                            if "search" in block.text.lower():
                                if "WebSearch" not in tools_used:
                                    tools_used.append("WebSearch")

                            logger.debug(
                                f"Turn {turns_used} response received",
                                response_length=len(block.text),
                            )

            # Format reinforcement on final turn (if not at max_turns yet)
            if format_template and turns_used < max_turns:
                logger.info("Applying format reinforcement", turn=turns_used + 1)
                reinforcement_prompt = f"""
Please format your response as JSON matching this template:
{format_template}

Ensure the output is valid JSON that can be parsed.
"""
                await client.query(reinforcement_prompt)
                turns_used += 1
                conversation_log.append(
                    {"role": "user", "content": reinforcement_prompt}
                )

                # Get reinforced response
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                raw_response = block.text
                                conversation_log.append(
                                    {"role": "assistant", "content": block.text}
                                )

        # Parse response
        parsed_data = _parse_json_response(raw_response)
        format_valid = parsed_data is not None

        logger.info(
            "Agentic discovery complete",
            turns_used=turns_used,
            tools_used=tools_used,
            format_valid=format_valid,
            data_extracted=bool(parsed_data),
        )

        return {
            "data": parsed_data or {},
            "turns_used": turns_used,
            "tools_used": tools_used,
            "format_valid": format_valid,
            "raw_response": raw_response,
            "conversation_log": conversation_log,
        }

    except Exception as e:
        logger.error(
            "Agentic discovery failed",
            error=str(e),
            turns_used=turns_used,
        )
        raise


async def spawn_sub_agent(
    task_description: str,
    prompt: str,
    allowed_tools: list[str],
    correlation_id: str = "sub-agent",
) -> dict[str, Any]:
    """Spawn a specialized sub-agent via Task tool for targeted operation.

    Sub-agents are useful for:
    - Scraping individual professor profiles in parallel
    - Extracting specific data from detailed pages
    - Isolating failures (one sub-agent failure doesn't affect others)
    - Specialized prompts for specific tasks

    Args:
        task_description: Short description for Task tool (3-5 words)
        prompt: Detailed prompt for sub-agent
        allowed_tools: Tools available to sub-agent
        correlation_id: Correlation ID for logging

    Returns:
        dict with keys:
            - data: Sub-agent result
            - success: Whether sub-agent succeeded
            - error: Error message if failed

    Example:
        >>> result = await spawn_sub_agent(
        ...     task_description="Scrape professor profile",
        ...     prompt="Extract research areas from https://cs.edu/faculty/jsmith",
        ...     allowed_tools=["WebFetch"]
        ... )
        >>> print(result["data"])

    Story: Phase 1 POC - Sub-agent spawning
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="sub_agent",
        component="agentic_patterns",
    )
    logger.info("Spawning sub-agent", task_description=task_description)

    try:
        # TODO: Implement Task tool usage
        # This is a placeholder for Phase 1 POC
        # The Task tool from Claude Agent SDK should be used here
        # Example: task = Task(description=task_description, prompt=prompt, ...)

        # TEMPORARY: Direct implementation until Task tool pattern validated
        options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            max_turns=2,
            system_prompt="You are a specialized data extraction assistant.",
            setting_sources=None,
        )

        result_data = {}
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result_data = _parse_json_response(block.text) or {}

        logger.info("Sub-agent completed", success=bool(result_data))

        return {"data": result_data, "success": bool(result_data), "error": None}

    except Exception as e:
        logger.error("Sub-agent failed", error=str(e))
        return {"data": {}, "success": False, "error": str(e)}


async def multi_turn_with_format_reinforcement(
    client: ClaudeSDKClient,
    initial_prompt: str,
    max_turns: int,
    format_template: str,
    correlation_id: str = "multi-turn",
) -> str:
    """Execute multi-turn conversation with format reinforcement on final turn.

    This helper manages the conversation loop with format reinforcement.
    Use when you already have an initialized ClaudeSDKClient.

    Args:
        client: Initialized ClaudeSDKClient
        initial_prompt: Starting prompt
        max_turns: Maximum conversation turns
        format_template: JSON format template for final turn
        correlation_id: Correlation ID for logging

    Returns:
        Final formatted response text

    Raises:
        Exception: If conversation fails

    Story: Phase 1 POC - Format reinforcement pattern
    """
    logger = get_logger(
        correlation_id=correlation_id,
        phase="multi_turn",
        component="agentic_patterns",
    )

    turns_used = 0
    raw_response = ""

    # Initial query
    await client.query(initial_prompt)
    turns_used += 1

    # Collect response
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    raw_response = block.text

    # Format reinforcement
    if turns_used < max_turns:
        reinforcement = f"""
Please format your response as JSON matching this template:
{format_template}
"""
        await client.query(reinforcement)
        turns_used += 1

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        raw_response = block.text

    logger.info("Multi-turn conversation complete", turns_used=turns_used)
    return raw_response


def _parse_json_response(text: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Parse JSON from LLM response text.

    Tries multiple strategies:
    1. Direct JSON parsing
    2. Extract JSON array/object with regex
    3. Extract code block with ```json

    Args:
        text: Response text from LLM

    Returns:
        Parsed JSON data or None if parsing fails
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract JSON array
    json_array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if json_array_match:
        try:
            return json.loads(json_array_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract JSON object
    json_obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_obj_match:
        try:
            return json.loads(json_obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: Extract from code block
    code_block_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    return None


# TODO: Additional patterns to implement in Phase 1

async def agent_driven_tool_selection(
    url: str,
    required_fields: list[str],
    max_attempts: int = 3,
    correlation_id: str = "agent-tools",
) -> dict[str, Any]:
    """Agent autonomously decides which tools to use and when to escalate.

    This replaces the Python-orchestrated scrape_with_sufficiency pattern.
    The agent decides:
    - Try WebFetch first
    - Evaluate sufficiency
    - Decide if Puppeteer MCP needed
    - Escalate autonomously

    Args:
        url: URL to scrape
        required_fields: Fields that must be extracted
        max_attempts: Maximum attempts
        correlation_id: Correlation ID for logging

    Returns:
        dict with extracted data and metadata

    Story: Phase 1 POC - Agent-driven tool selection
    """
    # TODO: Implement in Phase 1
    # This is a key pattern to demonstrate agent autonomy
    logger = get_logger(
        correlation_id=correlation_id,
        phase="agent_tools",
        component="agentic_patterns",
    )
    logger.info(
        "Agent-driven tool selection not yet implemented",
        url=url,
        required_fields=required_fields,
    )
    raise NotImplementedError("Phase 1 POC: Implement agent-driven tool selection")


async def parallel_sub_agents(
    tasks: list[dict[str, str]], max_concurrent: int = 5
) -> list[dict[str, Any]]:
    """Spawn multiple sub-agents in parallel for batch operations.

    Args:
        tasks: List of task dicts with 'description' and 'prompt'
        max_concurrent: Maximum concurrent sub-agents

    Returns:
        List of results from all sub-agents

    Story: Phase 1 POC - Parallel sub-agent execution
    """
    # TODO: Implement in Phase 1
    # Combines sub-agent spawning with asyncio.gather() for parallel execution
    raise NotImplementedError("Phase 1 POC: Implement parallel sub-agents")

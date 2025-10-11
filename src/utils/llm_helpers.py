"""
LLM Helpers Module

Centralized LLM prompt templates and retry logic for all agent LLM interactions.
All LLM calls must go through this module - no inline prompts scattered in code.

Example Usage:
    from src.utils.llm_helpers import (
        analyze_department_relevance,
        filter_professor_research,
        match_linkedin_profile,
        call_llm_with_retry
    )

    # Department relevance
    is_relevant = await analyze_department_relevance(
        department_name="Computer Science",
        department_description="...",
        research_interests="machine learning, AI"
    )

    # Professor filtering
    result = await filter_professor_research(
        professor_name="Dr. Jane Smith",
        research_areas="computer vision, deep learning",
        user_profile=user_profile
    )
"""

import json
import logging
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)
from typing import Any, Optional, cast

from src.utils.prompt_loader import render_prompt

# Initialize logger
logger = structlog.get_logger(__name__)


def _extract_json_from_markdown(response_text: str) -> str:
    """Extract JSON from LLM response, removing markdown code block markers if present.

    Args:
        response_text: Raw text response from LLM

    Returns:
        Clean JSON string with code block markers removed
    """
    json_text = response_text.strip()

    # Remove markdown code block markers if present
    if json_text.startswith("```json"):
        json_text = json_text[7:]  # Remove ```json
    elif json_text.startswith("```"):
        json_text = json_text[3:]  # Remove ```

    if json_text.endswith("```"):
        json_text = json_text[:-3]  # Remove trailing ```

    return json_text.strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
)
async def call_llm_with_retry(
    prompt: str, max_retries: int = 3, correlation_id: Optional[str] = None
) -> str:
    """
    Call LLM with retry logic using exponential backoff.

    Args:
        prompt: The formatted prompt to send to the LLM
        max_retries: Maximum number of retry attempts (default: 3)
        correlation_id: Optional correlation ID for logging

    Returns:
        LLM response text

    Raises:
        Exception: If all retry attempts fail

    Note:
        - Uses tenacity for retry with exponential backoff
        - Logs all LLM calls at DEBUG level
        - Waits 2s, 4s, 8s between retries (exponential)
        - Uses claude_agent_sdk.ClaudeSDKClient for LLM calls
    """
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

    log = logger.bind(correlation_id=correlation_id) if correlation_id else logger

    log.debug("LLM call initiated", prompt_length=len(prompt))

    try:
        # Use ClaudeSDKClient for LLM calls
        # Configure for pure text analysis without codebase context
        options = ClaudeAgentOptions(
            max_turns=1,  # Stateless one-off operation
            allowed_tools=[],  # Disable all tools (no Read, Write, Bash, etc.)
            system_prompt="You are an expert text analyst. Respond directly to user prompts with the requested analysis.",
            setting_sources=None,  # Disable loading .claude/settings, CLAUDE.md, etc.
        )

        response_text = ""

        # Use async context manager for ClaudeSDKClient
        async with ClaudeSDKClient(options=options) as client:
            # Send the prompt
            await client.query(prompt)

            # Receive and collect the response
            async for message in client.receive_response():
                # Extract text content from response
                if hasattr(message, "content") and message.content:
                    for block in message.content:
                        if hasattr(block, "text"):
                            response_text += block.text

        if not response_text:
            raise ValueError("LLM returned empty response")

        log.debug("LLM call succeeded", response_length=len(response_text))
        return response_text.strip()

    except Exception as e:
        log.error("LLM call failed", error=str(e), prompt_length=len(prompt))
        raise


async def analyze_department_relevance(
    department_name: str,
    school: str,
    research_interests: str,
    degree: str,
    background: str,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Analyze if a department is relevant to user's research interests.

    Args:
        department_name: Name of the department
        school: Parent school/college name
        research_interests: User's research interests
        degree: User's degree program
        background: User's educational background
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'decision' ('include'/'exclude'), 'confidence' (0-100), and 'reasoning' (str)
    """
    prompt = render_prompt(
        "department/relevance_filter.j2",
        correlation_id=correlation_id,
        interests=research_interests,
        degree=degree,
        background=background,
        department_name=department_name,
        school=school,
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse JSON response
    try:
        json_text = _extract_json_from_markdown(response)
        result = json.loads(json_text)

        # Validate required fields
        if (
            "decision" not in result
            or "confidence" not in result
            or "reasoning" not in result
        ):
            logger.warning(
                "LLM response missing required fields, using defaults",
                response=response[:200],
                correlation_id=correlation_id,
            )
            return {
                "decision": "exclude",
                "confidence": 0,
                "reasoning": "Invalid response format",
            }

        return cast(dict[str, Any], result)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from LLM response",
            error=str(e),
            response=response[:200],
            correlation_id=correlation_id,
        )
        # Default to exclude on parse error
        return {"decision": "exclude", "confidence": 0, "reasoning": "JSON parse error"}


async def filter_professor_research(
    professor_name: str,
    research_areas: str,
    user_profile: str,
    bio: str = "",
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Filter professor by research alignment with user profile.

    Args:
        professor_name: Professor's name
        research_areas: Professor's research areas
        user_profile: User's research profile
        bio: Optional professor bio/description
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'confidence' (0-100) and 'reasoning' (str)
    """
    prompt = render_prompt(
        "professor/research_filter.j2",
        correlation_id=correlation_id,
        profile=user_profile,
        name=professor_name,
        research_areas=research_areas,
        bio=bio or "Not available",
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse JSON response
    try:
        json_text = _extract_json_from_markdown(response)
        result = json.loads(json_text)

        # Validate required fields
        if "confidence" not in result or "reasoning" not in result:
            logger.warning(
                "LLM response missing required fields, using defaults",
                response=response[:200],
                correlation_id=correlation_id,
            )
            return {"confidence": 0, "reasoning": "Invalid response format"}

        return cast(dict[str, Any], result)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from LLM response",
            error=str(e),
            response=response[:200],
            correlation_id=correlation_id,
        )
        # Default to low confidence on parse error
        return {"confidence": 0, "reasoning": "JSON parse error"}


async def match_linkedin_profile(
    member_name: str,
    university: str,
    lab_name: str,
    profile_data: str,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Match LinkedIn profile to lab member.

    Args:
        member_name: Lab member's name
        university: University/institution name
        lab_name: Lab/department name
        profile_data: LinkedIn profile data
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'confidence' (0-100) and 'reasoning' (str)
    """
    prompt = render_prompt(
        "linkedin/profile_match.j2",
        correlation_id=correlation_id,
        member_name=member_name,
        university=university,
        lab_name=lab_name,
        profile_data=profile_data,
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse JSON response
    try:
        json_text = _extract_json_from_markdown(response)
        result = json.loads(json_text)

        # Validate required fields
        if "confidence" not in result or "reasoning" not in result:
            logger.warning(
                "LLM response missing required fields, using defaults",
                response=response[:200],
                correlation_id=correlation_id,
            )
            return {"confidence": 0, "reasoning": "Invalid response format"}

        return cast(dict[str, Any], result)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from LLM response",
            error=str(e),
            response=response[:200],
            correlation_id=correlation_id,
        )
        # Default to low confidence on parse error
        return {"confidence": 0, "reasoning": "JSON parse error"}


async def match_names(
    name1: str, name2: str, context: str = "", correlation_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Determine if two names refer to the same person.

    Args:
        name1: First name
        name2: Second name
        context: Additional context for matching
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'decision' (yes/no), 'confidence' (0-100), and 'reasoning' (str)
    """
    prompt = render_prompt(
        "professor/name_match.j2",
        correlation_id=correlation_id,
        name1=name1,
        name2=name2,
        context=context or "No additional context",
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse JSON response
    try:
        json_text = _extract_json_from_markdown(response)
        result = json.loads(json_text)

        # Validate required fields
        if (
            "decision" not in result
            or "confidence" not in result
            or "reasoning" not in result
        ):
            logger.warning(
                "LLM response missing required fields, using defaults",
                response=response[:200],
                correlation_id=correlation_id,
            )
            return {
                "decision": "no",
                "confidence": 0,
                "reasoning": "Invalid response format",
            }

        return cast(dict[str, Any], result)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from LLM response",
            error=str(e),
            response=response[:200],
            correlation_id=correlation_id,
        )
        # Default to no match on parse error
        return {"decision": "no", "confidence": 0, "reasoning": "JSON parse error"}


async def score_abstract_relevance(
    paper_title: str,
    abstract: str,
    research_interests: str,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Score paper abstract relevance to user's research interests.

    Args:
        paper_title: Paper title
        abstract: Paper abstract text
        research_interests: User's research interests
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'relevance' (0-100) and 'reasoning' (str)
    """
    prompt = render_prompt(
        "publication/abstract_relevance.j2",
        correlation_id=correlation_id,
        interests=research_interests,
        abstract=abstract,
        title=paper_title,
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse JSON response
    try:
        json_text = _extract_json_from_markdown(response)
        result = json.loads(json_text)

        # Validate required fields
        if "relevance" not in result or "reasoning" not in result:
            logger.warning(
                "LLM response missing required fields, using defaults",
                response=response[:200],
                correlation_id=correlation_id,
            )
            return {"relevance": 0, "reasoning": "Invalid response format"}

        return cast(dict[str, Any], result)

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from LLM response",
            error=str(e),
            response=response[:200],
            correlation_id=correlation_id,
        )
        # Default to low relevance on parse error
        return {"relevance": 0, "reasoning": "JSON parse error"}

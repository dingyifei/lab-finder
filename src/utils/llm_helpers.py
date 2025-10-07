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
from typing import Any, Optional

# Initialize logger
logger = structlog.get_logger(__name__)


# Prompt Templates

DEPARTMENT_RELEVANCE_TEMPLATE = """Given the user's research interests: {interests}

Is the department "{department_name}" relevant to these interests?

Department Description:
{description}

Respond with:
- Yes/No
- Brief reasoning (1-2 sentences)

Format your response as:
Decision: [Yes/No]
Reasoning: [your reasoning]
"""

PROFESSOR_FILTER_TEMPLATE = """Given the user's research profile:
{profile}

Does Professor {name} with the following research areas match the user's interests?

Professor Research Areas:
{research_areas}

Professor Bio/Description (if available):
{bio}

Provide:
- Confidence score (0-100)
- Reasoning for the score

Format your response as:
Confidence: [0-100]
Reasoning: [your reasoning]
"""

LINKEDIN_MATCH_TEMPLATE = """Does this LinkedIn profile match the lab member?

Lab Member Name: {member_name}
University/Institution: {university}
Department/Lab: {lab_name}

LinkedIn Profile Data:
{profile_data}

Determine if these refer to the same person. Provide:
- Confidence score (0-100)
- Reasoning

Format your response as:
Confidence: [0-100]
Reasoning: [your reasoning]
"""

NAME_MATCH_TEMPLATE = """Are these the same person?

Name 1: {name1}
Name 2: {name2}

Additional Context:
{context}

Consider:
- Name variations (nicknames, middle names, initials)
- Cultural naming conventions
- Academic naming patterns (Dr., Prof., etc.)

Provide:
- Yes/No decision
- Confidence score (0-100)
- Reasoning

Format your response as:
Decision: [Yes/No]
Confidence: [0-100]
Reasoning: [your reasoning]
"""

ABSTRACT_RELEVANCE_TEMPLATE = """Rate the relevance of this paper abstract to the user's research interests.

User Research Interests:
{interests}

Paper Abstract:
{abstract}

Paper Title: {title}

Provide:
- Relevance score (0-100)
  - 0-20: Not relevant
  - 21-40: Tangentially related
  - 41-60: Moderately relevant
  - 61-80: Highly relevant
  - 81-100: Directly aligned
- Reasoning for the score

Format your response as:
Relevance: [0-100]
Reasoning: [your reasoning]
"""


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
    """
    log = logger.bind(correlation_id=correlation_id) if correlation_id else logger

    log.debug("LLM call initiated", prompt_length=len(prompt))

    try:
        # TODO: Replace with actual Claude SDK LLM call
        # This is a placeholder for the actual implementation
        # The Claude Agent SDK will provide the LLM client

        # For now, raise NotImplementedError
        # Actual implementation will be:
        # response = await claude_client.messages.create(
        #     model="claude-3-5-sonnet-20241022",
        #     max_tokens=1024,
        #     messages=[{"role": "user", "content": prompt}]
        # )
        # return response.content[0].text

        raise NotImplementedError(
            "LLM client not yet integrated. "
            "Replace this with actual Claude SDK call in agent implementation."
        )

    except Exception as e:
        log.error("LLM call failed", error=str(e), prompt_length=len(prompt))
        raise


async def analyze_department_relevance(
    department_name: str,
    department_description: str,
    research_interests: str,
    correlation_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Analyze if a department is relevant to user's research interests.

    Args:
        department_name: Name of the department
        department_description: Department description text
        research_interests: User's research interests
        correlation_id: Optional correlation ID for logging

    Returns:
        Dict with 'decision' (Yes/No) and 'reasoning' (str)
    """
    prompt = DEPARTMENT_RELEVANCE_TEMPLATE.format(
        interests=research_interests,
        department_name=department_name,
        description=department_description,
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse response (simple parsing, can be enhanced)
    lines = response.strip().split("\n")
    result = {"decision": "No", "reasoning": ""}

    for line in lines:
        if line.startswith("Decision:"):
            result["decision"] = line.split(":", 1)[1].strip()
        elif line.startswith("Reasoning:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result


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
    prompt = PROFESSOR_FILTER_TEMPLATE.format(
        profile=user_profile,
        name=professor_name,
        research_areas=research_areas,
        bio=bio or "Not available",
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse response
    lines = response.strip().split("\n")
    result = {"confidence": 0, "reasoning": ""}

    for line in lines:
        if line.startswith("Confidence:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["confidence"] = 0
        elif line.startswith("Reasoning:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result


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
    prompt = LINKEDIN_MATCH_TEMPLATE.format(
        member_name=member_name,
        university=university,
        lab_name=lab_name,
        profile_data=profile_data,
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse response
    lines = response.strip().split("\n")
    result = {"confidence": 0, "reasoning": ""}

    for line in lines:
        if line.startswith("Confidence:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["confidence"] = 0
        elif line.startswith("Reasoning:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result


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
        Dict with 'decision' (Yes/No), 'confidence' (0-100), and 'reasoning' (str)
    """
    prompt = NAME_MATCH_TEMPLATE.format(
        name1=name1, name2=name2, context=context or "No additional context"
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse response
    lines = response.strip().split("\n")
    result = {"decision": "No", "confidence": 0, "reasoning": ""}

    for line in lines:
        if line.startswith("Decision:"):
            result["decision"] = line.split(":", 1)[1].strip()
        elif line.startswith("Confidence:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["confidence"] = 0
        elif line.startswith("Reasoning:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result


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
    prompt = ABSTRACT_RELEVANCE_TEMPLATE.format(
        interests=research_interests, abstract=abstract, title=paper_title
    )

    response = await call_llm_with_retry(prompt, correlation_id=correlation_id)

    # Parse response
    lines = response.strip().split("\n")
    result = {"relevance": 0, "reasoning": ""}

    for line in lines:
        if line.startswith("Relevance:"):
            try:
                result["relevance"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                result["relevance"] = 0
        elif line.startswith("Reasoning:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result

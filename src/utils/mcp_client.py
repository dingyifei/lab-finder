"""MCP Server Configuration Helper

Provides configuration dictionaries for Claude Agent SDK to spawn and communicate
with MCP servers via STDIO transport. Does not handle MCP protocol communication
directly - that's managed by Claude Agent SDK.

MCP Servers Configured:
- paper-search-mcp: Academic publication retrieval (Epic 5)
- mcp-linkedin: LinkedIn profile matching (Epic 6)
"""

import os
import sys
from typing import TypedDict

from dotenv import load_dotenv


class MCPServerConfig(TypedDict):
    """Type definition for STDIO MCP server configuration."""

    type: str
    command: str
    args: list[str]
    env: dict[str, str] | None


def get_mcp_server_config() -> dict[str, MCPServerConfig]:
    """Return MCP server STDIO configuration for Claude Agent SDK.

    Loads LinkedIn credentials from environment variables and returns
    configuration dictionary that can be passed to ClaudeAgentOptions.

    Returns:
        dict: MCP server configurations with keys:
            - "papers": paper-search-mcp configuration
            - "linkedin": mcp-linkedin configuration

    Environment Variables Required:
        LINKEDIN_EMAIL: LinkedIn account email (for mcp-linkedin)
        LINKEDIN_PASSWORD: LinkedIn account password (for mcp-linkedin)

    Example:
        >>> from claude_agent_sdk import ClaudeAgentOptions
        >>> mcp_config = get_mcp_server_config()
        >>> options = ClaudeAgentOptions(mcp_servers=mcp_config)

    Notes:
        - paper-search-mcp runs via: python -m paper_search_mcp.server
        - mcp-linkedin runs via: uvx --from git+https://github.com/adhikasp/mcp-linkedin
        - Claude Agent SDK handles spawning, protocol communication, and cleanup
        - Application code accesses tools via: mcp__<server>__<tool>
    """
    # Load environment variables from .env file
    load_dotenv()

    # Get LinkedIn credentials from environment
    linkedin_email = os.getenv("LINKEDIN_EMAIL")
    linkedin_password = os.getenv("LINKEDIN_PASSWORD")

    # Build configuration dictionary
    config: dict[str, MCPServerConfig] = {
        "papers": {
            "type": "stdio",
            "command": sys.executable,  # Use current Python interpreter
            "args": ["-m", "paper_search_mcp.server"],
            "env": None,
        },
        "linkedin": {
            "type": "stdio",
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/adhikasp/mcp-linkedin",
                "mcp-linkedin",
            ],
            "env": {
                "LINKEDIN_EMAIL": linkedin_email or "",
                "LINKEDIN_PASSWORD": linkedin_password or "",
            },
        },
    }

    return config


def validate_mcp_config() -> tuple[bool, list[str]]:
    """Validate MCP server configuration and required credentials.

    Checks that required environment variables are set and non-empty.
    Does not test actual server connectivity - use integration tests for that.

    Returns:
        tuple: (is_valid: bool, errors: list[str])
            - is_valid: True if all required credentials are present
            - errors: List of missing credential error messages

    Example:
        >>> is_valid, errors = validate_mcp_config()
        >>> if not is_valid:
        ...     for error in errors:
        ...         logger.error(error)

    Fallback Pattern for MCP Server Failures:
        When MCP servers are unavailable, agents should:
        1. Catch MCP-related exceptions gracefully
        2. Log warning with structured logging
        3. Add data quality flag to results
        4. Continue pipeline execution

        Example fallback implementation (used in Epic 5 & 6):
        >>> try:
        ...     publications = await search_papers(author_name)
        ... except MCPServerUnavailable:
        ...     logger.warning("paper-search-mcp unavailable",
        ...                   professor=author_name)
        ...     lab_data.data_quality_flags.append("mcp_papers_unavailable")
        ...     publications = []  # Continue with empty list
    """
    load_dotenv()

    errors: list[str] = []

    # Check LinkedIn credentials
    if not os.getenv("LINKEDIN_EMAIL"):
        errors.append("LINKEDIN_EMAIL not set in .env file")

    if not os.getenv("LINKEDIN_PASSWORD"):
        errors.append("LINKEDIN_PASSWORD not set in .env file")

    is_valid = len(errors) == 0
    return is_valid, errors

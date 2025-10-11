"""Integration tests for MCP server configuration via .mcp.json.

Tests that .mcp.json is properly configured for Claude Agent SDK.
SDK handles actual server spawning and communication.
"""

import json
from pathlib import Path

import pytest


@pytest.mark.integration
class TestMCPConfigFile:
    """Test suite for .mcp.json configuration file."""

    def test_mcp_json_exists(self):
        """Test that claude/.mcp.json file exists."""
        mcp_config_path = Path("claude/.mcp.json")
        assert mcp_config_path.exists(), "claude/.mcp.json must exist for MCP server configuration"

    def test_mcp_json_is_valid_json(self):
        """Test that .mcp.json contains valid JSON."""
        mcp_config_path = Path("claude/.mcp.json")

        try:
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f".mcp.json contains invalid JSON: {e}")

        assert config is not None

    def test_mcp_json_has_required_structure(self):
        """Test that .mcp.json has required mcpServers structure."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "mcpServers" in config, ".mcp.json must have 'mcpServers' key"
        assert isinstance(config["mcpServers"], dict), "mcpServers must be a dictionary"

    def test_mcp_json_contains_required_servers(self):
        """Test that .mcp.json configures all three required MCP servers."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # All three servers must be configured
        assert "puppeteer" in servers, "puppeteer MCP server must be configured"
        assert "papers" in servers, "paper-search-mcp server must be configured"
        assert "linkedin" in servers, "mcp-linkedin server must be configured"

    def test_server_configs_have_required_fields(self):
        """Test that each server config has type, command, and args fields."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        for server_name, server_config in config["mcpServers"].items():
            assert "type" in server_config, f"{server_name} must have 'type' field"
            assert "command" in server_config, f"{server_name} must have 'command' field"
            assert "args" in server_config, f"{server_name} must have 'args' field"

            assert server_config["type"] == "stdio", f"{server_name} must use stdio transport"
            assert isinstance(server_config["command"], str), f"{server_name} command must be string"
            assert isinstance(server_config["args"], list), f"{server_name} args must be list"

    def test_puppeteer_mcp_config(self):
        """Test that Puppeteer MCP server has correct configuration."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        puppeteer = config["mcpServers"]["puppeteer"]

        assert puppeteer["command"] == "npx", "Puppeteer should use npx command"
        assert "@modelcontextprotocol/server-puppeteer" in puppeteer["args"], \
            "Puppeteer args must include @modelcontextprotocol/server-puppeteer"

    def test_papers_mcp_config(self):
        """Test that paper-search-mcp server has correct configuration."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        papers = config["mcpServers"]["papers"]

        assert papers["command"] == "python", "papers should use python command"
        assert "-m" in papers["args"], "papers args must include -m flag"
        assert "paper_search_mcp.server" in papers["args"], \
            "papers args must include paper_search_mcp.server module"

    def test_linkedin_mcp_config(self):
        """Test that mcp-linkedin server has correct configuration."""
        mcp_config_path = Path("claude/.mcp.json")

        with open(mcp_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        linkedin = config["mcpServers"]["linkedin"]

        assert linkedin["command"] == "uvx", "linkedin should use uvx command"
        assert "--from" in linkedin["args"], "linkedin args must include --from flag"
        assert "env" in linkedin, "linkedin must have env configuration"
        assert "LINKEDIN_EMAIL" in linkedin["env"], "linkedin env must have LINKEDIN_EMAIL"
        assert "LINKEDIN_PASSWORD" in linkedin["env"], "linkedin env must have LINKEDIN_PASSWORD"

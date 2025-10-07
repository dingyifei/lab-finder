"""Integration tests for MCP server launch and connectivity.

Tests that MCP servers can be spawned via their configured STDIO commands.
Does NOT test MCP protocol communication - Claude Agent SDK handles that.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.utils.mcp_client import get_mcp_server_config


@pytest.mark.integration
class TestPaperSearchMCPLaunch:
    """Test suite for paper-search-mcp server launch."""

    def test_paper_search_mcp_installed(self):
        """Test that paper-search-mcp package is installed and importable."""
        try:
            import paper_search_mcp

            assert paper_search_mcp is not None
        except ImportError:
            pytest.fail("paper-search-mcp package not installed")

    def test_paper_search_mcp_module_executable(self):
        """Test that paper-search-mcp server module can be executed."""
        # Arrange
        config = get_mcp_server_config()
        papers_config = config["papers"]

        # Act - Try to execute with timeout to prevent hanging
        # The server will start and wait for STDIO input, so we kill it quickly
        try:
            process = subprocess.Popen(
                [papers_config["command"]] + papers_config["args"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )

            # Give it a moment to start
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Server started and is waiting for input - this is success
                process.kill()
                process.wait()
                return

            # If process exited immediately, check for errors
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                pytest.fail(
                    f"paper-search-mcp failed to start:\n"
                    f"stdout: {stdout.decode()}\n"
                    f"stderr: {stderr.decode()}"
                )

        except FileNotFoundError:
            pytest.fail(f"Command not found: {papers_config['command']}")

    def test_config_has_correct_command(self):
        """Test that paper-search-mcp config uses correct Python interpreter."""
        # Arrange
        config = get_mcp_server_config()

        # Act
        papers_config = config["papers"]

        # Assert - should use current Python interpreter
        assert papers_config["command"] == sys.executable
        assert "-m" in papers_config["args"]
        assert "paper_search_mcp.server" in papers_config["args"]


@pytest.mark.integration
class TestMCPLinkedInLaunch:
    """Test suite for mcp-linkedin server launch via uvx."""

    def test_uvx_installed(self):
        """Test that uvx is installed and available."""
        uvx_path = shutil.which("uvx")
        if uvx_path is None:
            pytest.skip("uvx not installed (requires uv package)")
        assert Path(uvx_path).exists()

    @pytest.mark.slow
    def test_mcp_linkedin_can_be_fetched(self):
        """Test that uvx can fetch and run mcp-linkedin from git repository.

        Note: This test actually downloads the package, so it requires network
        access and may be slow. Skip if offline or for quick test runs.
        Use pytest -m "not slow" to skip this test.
        """
        # Skip if uvx not available
        uvx_path = shutil.which("uvx")
        if uvx_path is None:
            pytest.skip("uvx not installed")

        # Arrange
        config = get_mcp_server_config()
        linkedin_config = config["linkedin"]

        # Act - Try to spawn server (it will wait for STDIO input)
        try:
            process = subprocess.Popen(
                [linkedin_config["command"]] + linkedin_config["args"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                env=linkedin_config["env"],
            )

            # Give it time to download and start (first run takes longer)
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                # Server started and is waiting for input - this is success
                process.kill()
                process.wait()
                return

            # If process exited immediately, check for errors
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                # Ignore credential errors - we're just testing launch
                stderr_text = stderr.decode()
                if (
                    "LINKEDIN_EMAIL" in stderr_text
                    or "LINKEDIN_PASSWORD" in stderr_text
                ):
                    pytest.skip("Credentials not configured (expected for launch test)")

                # Ignore git/network errors - network may not be available
                if (
                    "Git operation failed" in stderr_text
                    or "Failed to resolve" in stderr_text
                ):
                    pytest.skip("Network/git access not available")

                pytest.fail(
                    f"mcp-linkedin failed to start:\n"
                    f"stdout: {stdout.decode()}\n"
                    f"stderr: {stderr_text}"
                )

        except FileNotFoundError:
            pytest.fail(f"Command not found: {linkedin_config['command']}")

    def test_config_has_correct_git_source(self):
        """Test that mcp-linkedin config points to correct git repository."""
        # Arrange
        config = get_mcp_server_config()

        # Act
        linkedin_config = config["linkedin"]

        # Assert
        assert linkedin_config["command"] == "uvx"
        assert "--from" in linkedin_config["args"]
        git_url_index = linkedin_config["args"].index("--from") + 1
        git_url = linkedin_config["args"][git_url_index]
        assert git_url == "git+https://github.com/adhikasp/mcp-linkedin"

    def test_config_includes_environment_variables(self):
        """Test that mcp-linkedin config includes LinkedIn credentials in env."""
        # Arrange
        config = get_mcp_server_config()

        # Act
        linkedin_config = config["linkedin"]

        # Assert
        assert linkedin_config["env"] is not None
        assert "LINKEDIN_EMAIL" in linkedin_config["env"]
        assert "LINKEDIN_PASSWORD" in linkedin_config["env"]


@pytest.mark.integration
class TestMCPServerConfigIntegration:
    """Integration tests for combined MCP server configuration."""

    def test_all_configured_servers_have_stdio_type(self):
        """Test that all servers use STDIO transport type."""
        # Arrange
        config = get_mcp_server_config()

        # Act & Assert
        for server_name, server_config in config.items():
            assert server_config["type"] == "stdio", (
                f"Server {server_name} should use STDIO transport"
            )

    def test_config_structure_matches_claude_agent_sdk_format(self):
        """Test that config structure matches ClaudeAgentOptions expectations."""
        # Arrange
        config = get_mcp_server_config()

        # Act & Assert - Verify structure for each server
        for server_name, server_config in config.items():
            # Required fields
            assert "type" in server_config
            assert "command" in server_config
            assert "args" in server_config

            # Type validation
            assert isinstance(server_config["type"], str)
            assert isinstance(server_config["command"], str)
            assert isinstance(server_config["args"], list)

            # Optional env field
            if "env" in server_config and server_config["env"] is not None:
                assert isinstance(server_config["env"], dict)

# Lab Finder

A Python-based tool for systematically discovering and analyzing research labs within target universities using the Claude Agent SDK.

## Overview

Lab Finder automates the research lab discovery process by:
- Discovering university department structures
- Identifying and filtering relevant professors
- Analyzing lab websites and publications
- Matching lab members via LinkedIn
- Generating comprehensive fitness reports

## Setup Instructions

### Prerequisites

- Python 3.11.7 or higher
- pip 23.3 or higher
- Node.js (for MCP servers)
- Git

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd lab-finder
   ```

2. **Create and activate virtual environment:**
   ```bash
   # On Windows:
   py -3.11 -m venv venv
   venv\Scripts\activate

   # On macOS/Linux:
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install pip-tools:**
   ```bash
   pip install pip-tools
   ```

4. **Compile and install dependencies:**
   ```bash
   # Generate requirements.txt with pinned versions
   pip-compile requirements.in

   # Install all dependencies
   pip install -r requirements.txt
   ```

5. **Install Playwright browser drivers:**
   ```bash
   playwright install chromium
   ```

6. **Verify installation:**
   ```bash
   python scripts/verify_dependencies.py
   ```

7. **Install MCP servers (required for Epics 5-6):**
   ```bash
   # See Story 1.5 for MCP server setup
   npm install -g @modelcontextprotocol/server-paper-search
   npm install -g mcp-linkedin
   ```

### Troubleshooting

**ImportError for claude-agent-sdk:**
- Verify the Claude Agent SDK version is compatible with Python 3.11.7
- Check for pre-release versions if stable release unavailable

**Playwright installation issues:**
- Run `playwright install --help` for platform-specific options
- On Linux, you may need system dependencies: `playwright install-deps`

**MCP server issues:**
- See Story 1.5: MCP Server Configuration & Testing

## Requirements

- Python 3.11.7
- Claude Agent SDK 0.1.1+
- MCP servers: paper-search-mcp, mcp-linkedin

## Documentation

- [Product Requirements](docs/prd.md)
- [Architecture](docs/architecture.md)

## License

_(To be determined)_

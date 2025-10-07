#!/usr/bin/env python3
"""
Dependency Verification Script
Tests critical imports to ensure all dependencies are correctly installed.
"""

import sys
from importlib import import_module

# Critical dependencies to verify
DEPENDENCIES = [
    ("claude_agent_sdk", "Claude Agent SDK"),
    ("playwright.sync_api", "Playwright"),
    ("httpx", "HTTPX"),
    ("waybackpy", "Waybackpy"),
    ("mcp", "MCP"),
    ("jsonschema", "JSON Schema"),
    ("dotenv", "python-dotenv"),
    ("pydantic", "Pydantic"),
    ("structlog", "Structlog"),
    ("rich", "Rich"),
    ("pandas", "Pandas"),
    ("jsonlines", "Jsonlines"),
    ("tenacity", "Tenacity"),
    ("aiolimiter", "aiolimiter"),
    ("pytest", "Pytest"),
    ("ruff", "Ruff"),
    ("mypy", "MyPy"),
]

def verify_imports():
    """Verify all critical imports work."""
    failed = []

    print("Verifying dependencies...\n")

    for module_name, display_name in DEPENDENCIES:
        try:
            import_module(module_name)
            print(f"[OK] {display_name}")
        except ImportError as e:
            print(f"[FAILED] {display_name}: {e}")
            failed.append(display_name)

    print(f"\n{'='*60}")

    if failed:
        print(f"[ERROR] {len(failed)} dependencies failed:")
        for name in failed:
            print(f"   - {name}")
        sys.exit(1)
    else:
        print("[SUCCESS] All dependencies verified successfully!")
        sys.exit(0)

if __name__ == "__main__":
    verify_imports()

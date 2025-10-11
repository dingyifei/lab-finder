"""Test ONLY agentic pattern in POC context."""

import anyio  # Use anyio instead of asyncio (SDK examples use anyio)
from src.models.department import Department
from src.agents.professor_discovery import discover_professors_for_department_agentic_poc


async def test_agentic_only():
    """Test only the agentic pattern, not the old pattern."""

    test_department = Department(
        id="test-simple",
        name="Test Department",
        school="Test School",
        url="https://example.com",
        is_relevant=True,
        relevance_reasoning="Test for POC",
        data_quality_flags=[],
    )

    print("=" * 80)
    print("Testing AGENTIC pattern ONLY")
    print("=" * 80)
    print(f"\nDepartment: {test_department.name}")
    print(f"URL: {test_department.url}\n")

    try:
        results = await discover_professors_for_department_agentic_poc(
            test_department, correlation_id="test-agentic-only"
        )
        print(f"\nSUCCESS! Found {len(results)} professors")
        if results:
            print(f"Sample: {results[0].name}")
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    anyio.run(test_agentic_only)  # Use anyio like SDK examples

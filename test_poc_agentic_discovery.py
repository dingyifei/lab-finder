"""POC Test Script for Agentic Discovery Pattern.

Sprint Change Proposal: SCP-2025-10-11 Phase 1
Tests the agentic professor discovery pattern vs. the old zero-shot pattern.

Usage:
    python test_poc_agentic_discovery.py
"""

import asyncio
import json
from src.models.department import Department
from src.agents.professor_discovery import (
    discover_professors_for_department,
    discover_professors_for_department_agentic_poc,
)


async def run_poc_comparison():
    """Run POC comparison between old and new patterns."""

    # Test department - Use simple example.com for testing
    # Stanford CS URL might be timing out or blocking requests
    test_department = Department(
        id="test-simple",
        name="Test Department",
        school="Test School",
        url="https://example.com",  # Simple test URL
        is_relevant=True,
        relevance_reasoning="Test department for POC",
        data_quality_flags=[],
    )

    print("=" * 80)
    print("PHASE 1 POC: Agentic Discovery Pattern Validation")
    print("=" * 80)
    print(f"\nTest Department: {test_department.name}")
    print(f"URL: {test_department.url}")
    print("\n" + "=" * 80)

    # Test 1: Old zero-shot pattern
    print("\n[TEST 1] Running OLD zero-shot pattern...")
    print("-" * 80)
    try:
        old_results = await discover_professors_for_department(
            test_department, correlation_id="poc-test-old"
        )
        print(" Old pattern completed")
        print(f"   Professors found: {len(old_results)}")
        if old_results:
            print(f"   Sample professor: {old_results[0].name}")
            print(f"   Research areas: {old_results[0].research_areas}")
            print(f"   Data quality flags: {old_results[0].data_quality_flags}")
    except Exception as e:
        print(f" Old pattern failed: {e}")
        old_results = []

    # Test 2: New agentic pattern
    print("\n[TEST 2] Running NEW agentic pattern (POC)...")
    print("-" * 80)
    try:
        new_results = await discover_professors_for_department_agentic_poc(
            test_department, correlation_id="poc-test-agentic"
        )
        print(" Agentic pattern completed")
        print(f"   Professors found: {len(new_results)}")
        if new_results:
            print(f"   Sample professor: {new_results[0].name}")
            print(f"   Research areas: {new_results[0].research_areas}")
            print(f"   Data quality flags: {new_results[0].data_quality_flags}")
    except Exception as e:
        print(f" Agentic pattern failed: {e}")
        new_results = []

    # Comparison
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    print("\n Professor Count:")
    print(f"   Old pattern:     {len(old_results)}")
    print(f"   Agentic pattern: {len(new_results)}")
    print(f"   Difference:      {len(new_results) - len(old_results):+d}")

    if old_results:
        avg_research_old = sum(len(p.research_areas) for p in old_results) / len(
            old_results
        )
        missing_email_old = sum(1 for p in old_results if not p.email)
        print("\n Old Pattern Metrics:")
        print(f"   Avg research areas per prof: {avg_research_old:.2f}")
        print(f"   Missing emails: {missing_email_old}")

    if new_results:
        avg_research_new = sum(len(p.research_areas) for p in new_results) / len(
            new_results
        )
        missing_email_new = sum(1 for p in new_results if not p.email)
        print("\n Agentic Pattern Metrics:")
        print(f"   Avg research areas per prof: {avg_research_new:.2f}")
        print(f"   Missing emails: {missing_email_new}")

    print("\n" + "=" * 80)
    print("POC VALIDATION SUMMARY")
    print("=" * 80)

    # Success criteria check
    success_criteria = {
        "professors_found": len(new_results) > 0,
        "comparable_count": abs(len(new_results) - len(old_results)) <= len(old_results)
        * 0.5
        if old_results
        else len(new_results) > 0,
        "has_agentic_flag": any("agentic_discovery_poc" in p.data_quality_flags for p in new_results),
    }

    print("\n Success Criteria:")
    for criterion, passed in success_criteria.items():
        status = " PASS" if passed else " FAIL"
        print(f"   {status} - {criterion}")

    overall_pass = all(success_criteria.values())
    print(f"\n{'='*80}")
    if overall_pass:
        print(" POC VALIDATION: PASSED")
        print("   Ready to proceed to Phase 1 Day 2-3 (sub-agents)")
    else:
        print("  POC VALIDATION: NEEDS REVIEW")
        print("   Review logs and adjust pattern before proceeding")
    print("=" * 80)

    # Save results for analysis
    results_summary = {
        "test_department": {
            "name": test_department.name,
            "url": test_department.url,
        },
        "old_pattern": {
            "count": len(old_results),
            "sample": old_results[0].model_dump() if old_results else None,
        },
        "agentic_pattern": {
            "count": len(new_results),
            "sample": new_results[0].model_dump() if new_results else None,
        },
        "success_criteria": success_criteria,
        "overall_pass": overall_pass,
    }

    with open("poc_validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)

    print("\n Results saved to: poc_validation_results.json")
    print("\n Next steps:")
    if overall_pass:
        print("   1. Review conversation logs in logs/lab-finder.log")
        print("   2. Update PHASE-1-POC-HANDOFF.md with findings")
        print("   3. Proceed to implement sub-agent spawning")
    else:
        print("   1. Review error logs")
        print("   2. Debug agentic pattern issues")
        print("   3. Re-run POC test")


if __name__ == "__main__":
    print("\n>>> Starting POC validation...")
    print("This will test both old and new patterns\n")
    asyncio.run(run_poc_comparison())

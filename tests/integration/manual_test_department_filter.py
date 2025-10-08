"""Manual test for Story 2.3 department filtering with real LLM."""

import asyncio
from src.utils.llm_helpers import analyze_department_relevance


async def test_department_filtering():
    """Test that LLM integration works for department filtering."""

    print("Testing Story 2.3: Department Relevance Filtering")
    print("=" * 60)

    # Test case 1: Relevant department
    print("\nTest 1: Computer Science department (should be RELEVANT)")
    print("-" * 60)

    result1 = await analyze_department_relevance(
        department_name="Computer Science",
        school="School of Engineering",
        research_interests="Machine learning, artificial intelligence, and deep learning",
        degree="PhD in Computer Science",
        background="MS in CS from UC Berkeley with focus on ML",
        correlation_id="test-dept-filter-1"
    )

    print(f"Decision: {result1['decision']}")
    print(f"Confidence: {result1['confidence']}")
    print(f"Reasoning: {result1['reasoning']}")

    assert result1['decision'] == 'include', f"Expected 'include', got '{result1['decision']}'"
    assert result1['confidence'] > 70, f"Expected confidence > 70, got {result1['confidence']}"
    print("[PASS] Test 1 PASSED")

    # Test case 2: Irrelevant department
    print("\n\nTest 2: English Literature department (should be EXCLUDED)")
    print("-" * 60)

    result2 = await analyze_department_relevance(
        department_name="English Literature",
        school="School of Humanities",
        research_interests="Machine learning, artificial intelligence, and deep learning",
        degree="PhD in Computer Science",
        background="MS in CS from UC Berkeley with focus on ML",
        correlation_id="test-dept-filter-2"
    )

    print(f"Decision: {result2['decision']}")
    print(f"Confidence: {result2['confidence']}")
    print(f"Reasoning: {result2['reasoning']}")

    assert result2['decision'] == 'exclude', f"Expected 'exclude', got '{result2['decision']}'"
    print("[PASS] Test 2 PASSED")

    # Test case 3: Borderline/interdisciplinary department
    print("\n\nTest 3: Computational Biology (should be INCLUDED - interdisciplinary)")
    print("-" * 60)

    result3 = await analyze_department_relevance(
        department_name="Computational Biology",
        school="School of Medicine",
        research_interests="Machine learning, artificial intelligence, and deep learning",
        degree="PhD in Computer Science",
        background="MS in CS from UC Berkeley with focus on ML",
        correlation_id="test-dept-filter-3"
    )

    print(f"Decision: {result3['decision']}")
    print(f"Confidence: {result3['confidence']}")
    print(f"Reasoning: {result3['reasoning']}")

    # Should include due to "ANY potential overlap" guideline
    assert result3['decision'] == 'include', f"Expected 'include', got '{result3['decision']}'"
    print("[PASS] Test 3 PASSED")

    print("\n" + "=" * 60)
    print("[PASS] Story 2.3 Integration Test PASSED (3/3 tests)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_department_filtering())
    except NotImplementedError as e:
        print(f"\n[FAIL] {e}")
        print("\nThe LLM helper is still not implemented.")
        print("Please fix src/utils/llm_helpers.py")
    except Exception as e:
        print(f"\n[FAIL] {e}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

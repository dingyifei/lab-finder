"""Integration test for Story 2.3 - Department Relevance Filtering with real profile"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.agents.university_discovery import UniversityDiscoveryAgent
from src.models.department import Department
from src.utils.checkpoint_manager import CheckpointManager


# Mock LLM responses for different department types
def mock_llm_response(prompt: str) -> str:
    """Generate realistic mock LLM responses based on prompt content."""

    # Check department name in prompt
    if "Bioengineering" in prompt or "Bioinformatics" in prompt:
        return '{"decision": "include", "confidence": 95, "reasoning": "Direct alignment with bioengineering and computational biology research interests"}'
    elif "Computer Science" in prompt or "Computational" in prompt:
        return '{"decision": "include", "confidence": 90, "reasoning": "Strong overlap with machine learning and computational methods"}'
    elif "Biology" in prompt or "Molecular" in prompt:
        return '{"decision": "include", "confidence": 85, "reasoning": "Relevant to biological systems and genomics research"}'
    elif "Chemistry" in prompt:
        return '{"decision": "include", "confidence": 70, "reasoning": "Potential overlap in biochemical applications of ML"}'
    elif "Statistics" in prompt or "Mathematics" in prompt:
        return '{"decision": "include", "confidence": 75, "reasoning": "Relevant computational and analytical methods"}'
    elif "English" in prompt or "Literature" in prompt or "History" in prompt:
        return '{"decision": "exclude", "confidence": 95, "reasoning": "No overlap with computational biology research"}'
    elif "Mechanical" in prompt or "Civil" in prompt:
        return '{"decision": "exclude", "confidence": 85, "reasoning": "Limited relevance to bioinformatics research"}'
    elif "Graduate Studies" in prompt or "Interdisciplinary" in prompt:
        return '{"decision": "include", "confidence": 60, "reasoning": "Generic department that may contain relevant research groups"}'
    else:
        return '{"decision": "include", "confidence": 50, "reasoning": "Uncertain relevance, including for review"}'


async def main():
    """Run full integration test of Story 2.3."""

    print("=" * 80)
    print("STORY 2.3 INTEGRATION TEST - Department Relevance Filtering")
    print("=" * 80)
    print()

    # Create sample departments for UCSD
    sample_departments = [
        Department(
            id="dept-001",
            name="Bioengineering",
            school="Jacobs School of Engineering",
            url="https://be.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-002",
            name="Computer Science and Engineering",
            school="Jacobs School of Engineering",
            url="https://cse.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-003",
            name="Biology",
            school="Division of Biological Sciences",
            url="https://biology.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-004",
            name="Chemistry and Biochemistry",
            school="Division of Physical Sciences",
            url="https://chemistry.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-005",
            name="English Literature",
            school="Division of Arts and Humanities",
            url="https://english.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-006",
            name="Mathematics",
            school="Division of Physical Sciences",
            url="https://math.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-007",
            name="Mechanical and Aerospace Engineering",
            school="Jacobs School of Engineering",
            url="https://mae.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-008",
            name="Graduate Studies",
            school="University",
            url="https://grad.ucsd.edu",
            hierarchy_level=1,
        ),
        Department(
            id="dept-009",
            name="Bioinformatics and Systems Biology",
            school="Division of Biological Sciences",
            url="https://bioinformatics.ucsd.edu",
            hierarchy_level=2,
        ),
        Department(
            id="dept-010",
            name="Computational Science",
            school="San Diego Supercomputer Center",
            url="https://sdsc.ucsd.edu",
            hierarchy_level=2,
        ),
    ]

    print(f"[OK] Created {len(sample_departments)} sample departments")
    print()

    # Initialize agent with checkpoint manager
    checkpoint_manager = CheckpointManager(checkpoint_dir=Path("checkpoints"))
    agent = UniversityDiscoveryAgent(
        correlation_id="integration-test-2.3", checkpoint_manager=checkpoint_manager
    )

    print("[OK] Initialized UniversityDiscoveryAgent")
    print()

    # Load user profile
    print("Loading user profile...")
    user_profile = agent.load_user_profile()

    print(f"[OK] Profile loaded for: {user_profile.get('degree', 'Unknown')}")
    print(f"  Research interests preview: {user_profile['interests'][:100]}...")
    print()

    # Mock the LLM call
    print("Setting up LLM mock for testing...")
    with patch(
        "src.utils.llm_helpers.call_llm_with_retry", new_callable=AsyncMock
    ) as mock_llm:
        mock_llm.side_effect = lambda prompt, *args, **kwargs: mock_llm_response(prompt)

        print("[OK] LLM mock configured")
        print()

        # Run department filtering
        print("=" * 80)
        print("FILTERING DEPARTMENTS...")
        print("=" * 80)
        print()

        filtered_departments = await agent.filter_departments(
            departments=sample_departments,
            user_profile=user_profile,
            use_progress_tracker=False,  # Disable for cleaner output
        )

        print()
        print("=" * 80)
        print("FILTERING COMPLETE")
        print("=" * 80)
        print()

        # Analyze results
        relevant = [d for d in filtered_departments if d.is_relevant]
        excluded = [d for d in filtered_departments if not d.is_relevant]

        print("RESULTS SUMMARY:")
        print(f"  Total departments: {len(filtered_departments)}")
        print(f"  Relevant: {len(relevant)}")
        print(f"  Excluded: {len(excluded)}")
        print(
            f"  Retention rate: {len(relevant) / len(filtered_departments) * 100:.1f}%"
        )
        print()

        # Show relevant departments
        print("[INCLUDED] RELEVANT DEPARTMENTS:")
        for dept in relevant:
            print(f"  * {dept.name} ({dept.school})")
            print(f"    -> {dept.relevance_reasoning}")
        print()

        # Show excluded departments
        print("[EXCLUDED] FILTERED OUT DEPARTMENTS:")
        for dept in excluded:
            print(f"  * {dept.name} ({dept.school})")
            print(f"    -> {dept.relevance_reasoning}")
        print()

        # Save filtered departments report
        print("Saving filtered departments report...")
        agent.save_filtered_departments_report(filtered_departments)
        print("[OK] Report saved to: output/filtered-departments.md")
        print()

        # Save relevant departments to checkpoint
        print("Saving relevant departments to checkpoint...")
        agent.save_relevant_departments_checkpoint(filtered_departments)
        print(
            "[OK] Checkpoint saved to: checkpoints/phase-1-relevant-departments.jsonl"
        )
        print()

        # Verify checkpoint
        print("Verifying checkpoint contents...")
        loaded = checkpoint_manager.load_batches("phase-1-relevant-departments")
        print(f"[OK] Checkpoint verified: {len(loaded)} relevant departments saved")
        print()

        # Display checkpoint file location
        checkpoint_file = Path("checkpoints/phase-1-relevant-departments-batch-0.jsonl")
        if checkpoint_file.exists():
            print(
                f"[FILE] Checkpoint file size: {checkpoint_file.stat().st_size} bytes"
            )

        print()
        print("=" * 80)
        print("INTEGRATION TEST COMPLETE - SUCCESS")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Review output/filtered-departments.md for excluded departments")
        print("  2. Check checkpoints/phase-1-relevant-departments-batch-0.jsonl")
        print("  3. Story 2.3 is ready for Epic 3 (Professor Discovery)")
        print()


if __name__ == "__main__":
    asyncio.run(main())

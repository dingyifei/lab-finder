"""Manual test for Story 1.7 profile consolidation with real LLM."""

import asyncio
from src.agents.profile_consolidator import ProfileConsolidator


async def test_profile_consolidation():
    """Test that LLM integration works for profile consolidation."""

    print("Testing Story 1.7: User Profile Consolidation")
    print("=" * 60)

    # Sample user profile with REALISTIC research interest descriptions
    user_profile = {
        "name": "Test User",
        "current_degree": "PhD in Computer Science",
        "target_university": "Stanford University",
        "target_department": "Computer Science",
        "research_interests": [
            "My research focuses on developing scalable deep learning algorithms for natural language understanding, with particular emphasis on transformer architectures and their applications to multilingual text processing. I'm interested in improving model efficiency and interpretability while maintaining high performance across diverse linguistic contexts.",
            "I work on computer vision systems for autonomous vehicles, specifically addressing challenges in real-time object detection, semantic segmentation, and scene understanding under varying environmental conditions. My approach combines traditional computer vision techniques with modern deep learning methods.",
            "I'm passionate about the intersection of AI and healthcare, particularly using machine learning for early disease detection from medical imaging data. My work involves developing novel neural network architectures that can learn from limited labeled data while providing clinically interpretable predictions."
        ],
        "resume_highlights": {
            "education": [
                {
                    "degree": "MS in Computer Science",
                    "institution": "UC Berkeley",
                    "year": 2022
                }
            ],
            "skills": ["Python", "TensorFlow", "PyTorch", "Research Writing"],
            "research_experience": [
                {
                    "title": "Research Assistant",
                    "description": "Developed transformer models for question answering",
                    "duration": "2021-2022"
                }
            ]
        },
        "preferred_graduation_duration": 5.5
    }

    university_config = {
        "core_website": "https://www.stanford.edu",
        "university_name": "Stanford University"
    }

    # Test consolidation
    consolidator = ProfileConsolidator()

    try:
        print("\n1. Consolidating profile (this will call LLM)...")
        profile = await consolidator.consolidate(user_profile, university_config)

        print("\n[SUCCESS] Profile consolidated!")
        print("\nStreamlined Interests (LLM-generated):")
        print("-" * 60)
        print(profile.streamlined_interests)
        print("-" * 60)

        print("\n2. Saving markdown output...")
        markdown_path = consolidator.save_markdown(profile)
        print(f"[OK] Markdown saved to: {markdown_path}")

        print("\n3. Saving checkpoint...")
        consolidator.save_checkpoint(profile)
        print("[OK] Checkpoint saved to: checkpoints/phase-0-validation.json")

        print("\n" + "=" * 60)
        print("[PASS] Story 1.7 Integration Test PASSED")
        print("=" * 60)

    except NotImplementedError as e:
        print(f"\n[FAIL] {e}")
        print("\nThe LLM helper is still not implemented.")
        print("Please fix src/utils/llm_helpers.py")

    except Exception as e:
        print(f"\n[FAIL] {e}")
        print(f"\nError type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_profile_consolidation())

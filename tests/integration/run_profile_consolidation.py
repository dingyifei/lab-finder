"""
Execute Story 1.7 - User Profile Consolidation

Generates output/user-profile.md from config files using actual LLM integration.
"""

import asyncio
import json
from pathlib import Path

from src.agents.profile_consolidator import ProfileConsolidator


async def main():
    """Run profile consolidation end-to-end."""

    print("=" * 80)
    print("STORY 1.7: USER PROFILE CONSOLIDATION")
    print("=" * 80)
    print()

    # Load config files
    print("Loading configuration files...")

    user_profile_path = Path("config/user_profile.json")
    university_config_path = Path("config/university_config.json")

    if not user_profile_path.exists():
        print(f"ERROR: {user_profile_path} not found")
        return

    if not university_config_path.exists():
        print(f"ERROR: {university_config_path} not found")
        return

    with open(user_profile_path) as f:
        user_profile = json.load(f)

    with open(university_config_path) as f:
        university_config = json.load(f)

    print(f"[OK] Loaded user_profile.json")
    print(f"[OK] Loaded university_config.json")
    print()

    # Initialize ProfileConsolidator
    print("Initializing ProfileConsolidator...")
    consolidator = ProfileConsolidator()
    print("[OK] ProfileConsolidator initialized")
    print()

    # Consolidate profile (includes LLM call for interest streamlining)
    print("Consolidating profile...")
    print("  - Extracting education background")
    print("  - Extracting skills")
    print("  - Extracting research experience")
    print("  - Extracting qualifications")
    print("  - Streamlining research interests with LLM... (this may take a few seconds)")
    print()

    profile = await consolidator.consolidate(user_profile, university_config)

    print("[OK] Profile consolidated successfully")
    print()

    # Save markdown
    print("Saving markdown output...")
    markdown_path = consolidator.save_markdown(profile)
    print(f"[OK] Markdown saved to: {markdown_path}")
    print()

    # Save checkpoint
    print("Saving checkpoint...")
    consolidator.save_checkpoint(profile)
    print("[OK] Checkpoint saved to: checkpoints/phase-0-validation.json")
    print()

    # Display preview
    print("=" * 80)
    print("PROFILE PREVIEW")
    print("=" * 80)
    print()
    print(f"Name: {profile.name}")
    print(f"Degree: {profile.current_degree}")
    print(f"Target: {profile.target_university} - {profile.target_department}")
    print()
    print("Streamlined Research Interests:")
    print(f"  {profile.streamlined_interests}")
    print()
    print("=" * 80)
    print("SUCCESS - Story 1.7 Complete!")
    print("=" * 80)
    print()
    print(f"Next step: Review {markdown_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

# Database Schema

Lab Finder uses **JSONL checkpoint files** instead of a traditional database. Each phase writes batch checkpoints in JSONL format (one JSON object per line).

## Checkpoint Directory Structure

```
checkpoints/
├── phase-0-validation.json           # Single JSON (not batched)
├── phase-1-departments.jsonl         # Department records
├── phase-2-professors-batch-1.jsonl  # Batch 1 of professors
├── phase-2-professors-batch-2.jsonl  # Batch 2 of professors
├── phase-2-professors-batch-N.jsonl  # Batch N of professors
├── phase-3-labs-batch-1.jsonl        # Batch 1 of lab website data
├── phase-3-labs-batch-N.jsonl
├── phase-3-publications-batch-1.jsonl
├── phase-3-publications-batch-N.jsonl
├── phase-4-linkedin-batch-1.jsonl    # LinkedIn match results
├── phase-4-linkedin-batch-N.jsonl
├── phase-5-authorship.jsonl          # Authorship analysis
├── phase-5-scores.jsonl              # Fitness scores
└── _phase_completion_markers.json    # Tracks which phases are complete
```

## JSONL Schema Definitions

**Phase 0: User Profile (Single JSON)**
```json
{
  "name": "John Doe",
  "current_degree": "PhD in Computer Science",
  "target_university": "Stanford University",
  "target_department": "Computer Science",
  "research_interests": ["Machine Learning", "Computer Vision"],
  "resume_highlights": {
    "education": ["BS CS - MIT 2020", "MS CS - Stanford 2022"],
    "skills": ["Python", "PyTorch", "Research"],
    "research_experience": "2 years in CV lab at MIT"
  },
  "preferred_graduation_duration": 5.5
}
```

**Phase 1: Departments (JSONL)**
```jsonl
{"id": "dept-001", "name": "Computer Science", "school": "School of Engineering", "division": null, "url": "https://cs.stanford.edu", "hierarchy_level": 2, "is_relevant": true, "relevance_reasoning": "Direct match with user's CS degree and ML interests"}
{"id": "dept-002", "name": "Electrical Engineering", "school": "School of Engineering", "division": null, "url": "https://ee.stanford.edu", "hierarchy_level": 2, "is_relevant": true, "relevance_reasoning": "EE has strong ML/CV groups relevant to research interests"}
```

**Phase 2: Professors (JSONL batches)**
```jsonl
{"id": "prof-001", "name": "Dr. Jane Smith", "title": "Associate Professor", "department_id": "dept-001", "lab_name": "Vision Lab", "lab_url": "https://vision.stanford.edu", "email": "jsmith@stanford.edu", "research_areas": ["Computer Vision", "Deep Learning"], "is_filtered": false, "filter_confidence": 95.0, "filter_reasoning": "Strong alignment with CV and ML interests"}
{"id": "prof-002", "name": "Dr. Bob Johnson", "title": "Full Professor", "department_id": "dept-001", "lab_name": null, "lab_url": null, "email": "bjohnson@stanford.edu", "research_areas": ["Theory", "Algorithms"], "is_filtered": true, "filter_confidence": 88.0, "filter_reasoning": "No overlap with ML/CV interests, focus on pure theory"}
```

**Phase 3: Labs (JSONL batches)**
```jsonl
{"id": "lab-001", "pi_id": "prof-001", "name": "Vision Lab", "url": "https://vision.stanford.edu", "description": "Research in computer vision and deep learning", "last_updated": "2024-09-15", "wayback_history": ["2024-09-15", "2024-06-01", "2024-03-12"], "update_frequency": "monthly", "contact_email": "vision-lab@stanford.edu", "contact_form_url": null, "application_url": "https://vision.stanford.edu/join", "members": [], "members_inferred": false, "data_quality_flags": []}
```

**Phase 3: Publications (JSONL batches)**
```jsonl
{"id": "10.1234/example", "title": "Deep Learning for Image Recognition", "authors": ["Jane Smith", "Alice Cooper", "Bob Wilson"], "journal": "IEEE CVPR", "year": 2024, "abstract": "We propose a novel...", "acknowledgments": "Funded by NSF...", "doi": "10.1234/example", "url": "https://arxiv.org/...", "journal_sjr_score": 1.85, "first_author": "Jane Smith", "last_author": "Bob Wilson", "pi_author_position": "first", "relevance_score": 92.5, "is_collaborative": false}
```

**Phase 4: LinkedIn Matches (JSONL batches)**
```jsonl
{"id": "member-001", "lab_id": "lab-001", "name": "Alice Cooper", "role": "PhD Student", "entry_year": 2020, "is_inferred": false, "inference_confidence": null, "linkedin_profile_url": "https://linkedin.com/in/alicecooper", "linkedin_match_confidence": 95.0, "expected_graduation_year": 2025, "is_graduating_soon": true, "recently_departed": false}
```

**Phase 5: Fitness Scores (JSONL)**
```jsonl
{"lab_id": "lab-001", "overall_score": 88.5, "criteria_scores": {"research_alignment": 95.0, "publication_quality": 85.0, "position_availability": 90.0, "website_freshness": 80.0}, "criteria_weights": {"research_alignment": 0.4, "publication_quality": 0.3, "position_availability": 0.2, "website_freshness": 0.1}, "scoring_rationale": "Excellent match based on strong CV/ML alignment, high-quality recent publications, and upcoming PhD graduation creating position opening", "key_highlights": ["Top-tier CVPR publications", "1 PhD graduating in 2025", "Active lab with monthly website updates"], "position_availability": true, "priority_recommendation": 1}
```

## Checkpoint Loading Strategy

1. **Resumability:** CLI Coordinator checks `_phase_completion_markers.json` to determine last completed phase
2. **Batch Loading:** For incomplete phases, load all completed batches (e.g., `phase-2-professors-batch-*.jsonl`)
3. **Memory Management:** Load checkpoints into Python lists of Pydantic models for processing
4. **Deduplication:** When loading batches, deduplicate by ID (later batches override earlier if IDs collide)

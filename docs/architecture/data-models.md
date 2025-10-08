# Data Models

These models represent the core domain entities flowing through the Lab Finder pipeline. All models are implemented as Pydantic classes with optional fields to support graceful degradation.

## User Profile

**Purpose:** Consolidated baseline for all matching and filtering operations (FR6)

**Key Attributes:**
- `name`: str - User's full name
- `current_degree`: str - Current degree program (e.g., "PhD in Computer Science")
- `target_university`: str - University being analyzed
- `target_department`: str - Primary department of interest
- `research_interests`: list[str] - Streamlined research interest statements
- `resume_highlights`: dict - Extracted resume sections (education, skills, research experience)
- `preferred_graduation_duration`: float - Average PhD duration for timeline calculations (FR5, default: 5.5)

**Relationships:**
- Used by Department Filter to identify relevant departments
- Used by Professor Filter to match research fields
- Used by Fitness Scorer to calculate alignment scores

---

## Department

**Purpose:** Represents university organizational structure (FR7-FR8)

**Key Attributes:**
- `id`: str - Unique identifier (generated)
- `name`: str - Department name
- `school`: Optional[str] - Parent school/college
- `division`: Optional[str] - Parent division
- `url`: str - Department homepage URL
- `hierarchy_level`: int - Depth in organizational tree (0=school, 1=division, 2=department)
- `data_quality_flags`: list[str] - Quality issues (e.g., "missing_url", "missing_school", "ambiguous_hierarchy", "partial_metadata", "inference_based", "manual_entry", "scraping_failed")
- `is_relevant`: bool - Result of relevance filtering (FR9)
- `relevance_reasoning`: str - LLM explanation for filter decision

**Relationships:**
- One Department → Many Professors
- Departments form hierarchical tree structure

---

## Professor

**Purpose:** Faculty member with potential lab affiliation (FR10-FR13)

**Key Attributes:**
- `id`: str - Unique identifier (generated)
- `name`: str - Full name
- `title`: Optional[str] - Academic title
- `department_id`: str - Reference to Department
- `lab_name`: Optional[str] - Lab affiliation
- `lab_url`: Optional[str] - Lab website URL
- `email`: Optional[str] - Contact email (FR20)
- `research_areas`: list[str] - Research field descriptions from directory
- `is_filtered`: bool - Passed professor filter (FR11)
- `filter_confidence`: float - LLM confidence score 0-100 (FR12)
- `filter_reasoning`: str - Explanation for filter decision (FR13)

**Relationships:**
- Many Professors → One Department
- One Professor → One Lab (professor is the PI)
- One Professor → Many Publications

---

## Lab

**Purpose:** Research group with website, members, and publications (FR14-FR20)

**Key Attributes:**
- `id`: str - Unique identifier (generated)
- `pi_id`: str - Reference to Professor (principal investigator)
- `name`: str - Lab name
- `url`: Optional[str] - Lab website URL
- `description`: Optional[str] - Lab research focus from website
- `last_updated`: Optional[str] - Website last modification date (FR14)
- `wayback_history`: list[str] - Archive.org snapshot dates (FR14)
- `update_frequency`: Optional[str] - Website update pattern (monthly/yearly/stale)
- `contact_email`: Optional[str] - Lab contact email (FR20)
- `contact_form_url`: Optional[str] - Contact form URL (FR20)
- `application_url`: Optional[str] - Prospective student application URL (FR20)
- `members`: list[LabMember] - Current lab members (FR19)
- `members_inferred`: bool - Members inferred from co-authorship (FR31)
- `data_quality_flags`: list[str] - Missing data warnings (FR32)

**Relationships:**
- One Lab → One Professor (PI)
- One Lab → Many LabMembers
- One Lab → Many Publications (via PI and members)
- One Lab → Many Collaborations

---

## Lab Member

**Purpose:** Individual in research group (FR19, FR31)

**Key Attributes:**
- `id`: str - Unique identifier (generated)
- `lab_id`: str - Reference to Lab
- `name`: str - Full name
- `role`: Optional[str] - Position (PhD student, Postdoc, Research Scientist, etc.)
- `entry_year`: Optional[int] - Year joined lab
- `is_inferred`: bool - Inferred from co-authorship vs. listed on website (FR31)
- `inference_confidence`: Optional[float] - Confidence in inference 0-100
- `linkedin_profile_url`: Optional[str] - Matched LinkedIn profile (FR22)
- `linkedin_match_confidence`: Optional[float] - LLM match confidence 0-100 (FR22)
- `expected_graduation_year`: Optional[int] - Calculated from entry_year + duration (FR21)
- `is_graduating_soon`: bool - Within next year (FR21)
- `recently_departed`: bool - Graduated within last year (FR21)

**Relationships:**
- Many LabMembers → One Lab
- One LabMember → Many Publications (as co-author)
- One LabMember → One LinkedIn Profile (LLM-matched)

---

## Publication

**Purpose:** Research paper with authorship and journal metadata (FR15-FR17, FR30)

**Key Attributes:**
- `id`: str - Unique identifier (DOI or generated)
- `title`: str - Paper title
- `authors`: list[str] - Full author list in order
- `journal`: str - Journal or conference name
- `year`: int - Publication year
- `abstract`: Optional[str] - Paper abstract (FR30)
- `acknowledgments`: Optional[str] - Acknowledgment section (FR30)
- `doi`: Optional[str] - Digital Object Identifier
- `url`: Optional[str] - Paper URL
- `journal_sjr_score`: Optional[float] - Scimago Journal Rank score (FR17)
- `first_author`: str - First author name
- `last_author`: str - Last author name (often PI)
- `pi_author_position`: Optional[str] - PI's position in author list (first/last/middle)
- `relevance_score`: Optional[float] - LLM-assessed alignment with user interests
- `is_collaborative`: bool - External co-authors indicate collaboration (FR18)

**Relationships:**
- Many Publications → One Professor (as author)
- Many Publications → Many LabMembers (as co-authors)
- Many Publications → Many Collaborators (external)

---

## Collaboration

**Purpose:** Research partnership with external groups (FR18)

**Key Attributes:**
- `id`: str - Unique identifier (generated)
- `lab_id`: str - Reference to Lab
- `collaborator_name`: str - External researcher name
- `collaborator_institution`: str - External institution
- `frequency`: int - Number of co-authored papers
- `recent`: bool - Collaboration within last 3 years
- `papers`: list[str] - Publication IDs evidencing collaboration

**Relationships:**
- Many Collaborations → One Lab
- Many Collaborations → Many Publications

---

## Fitness Score

**Purpose:** Multi-factor lab ranking result (FR25)

**Key Attributes:**
- `lab_id`: str - Reference to Lab
- `overall_score`: float - Final fitness score 0-100
- `criteria_scores`: dict[str, float] - Score per criterion
- `criteria_weights`: dict[str, float] - Weight per criterion
- `scoring_rationale`: str - LLM explanation of score
- `key_highlights`: list[str] - Top factors influencing score
- `position_availability`: bool - Graduating PhD detected (FR21)
- `priority_recommendation`: int - Ranking tier (1=top priority, 2=strong candidate, 3=consider)

**Relationships:**
- One FitnessScore → One Lab
- Used to generate ranked Overview report (FR26)

---

## Data Model Design Principles

**1. LLM-Based Matching over Code Complexity:**
- **Name Matching:** Use LLM prompts to match professors/members across sources (directory, publications, LinkedIn) instead of algorithmic fuzzy matching
- **Profile Matching:** LLM evaluates candidate LinkedIn profiles considering name variations, affiliations, timelines (FR22)
- **Paper Deduplication:** LLM determines if papers with missing DOIs are duplicates based on title/authors/year
- **Rationale:** Claude Agent SDK provides LLM access; prompts handle edge cases (typos, name variants, institutional moves) better than code; dramatically reduces complexity

**2. Flexible Missing Data Handling:**
- All optional fields use `Optional[type]` in Pydantic models
- Validation checks for field presence but doesn't fail on missing data
- Missing fields tracked in `data_quality_flags` list for transparency in reports
- Processing continues with partial data; reports clearly indicate gaps with ⚠️ flags

**3. Denormalization for Pipeline Efficiency:**
- Some data duplicated (e.g., professor name in Publication authors and Professor entity) for query convenience
- JSONL files loaded into memory per phase; no complex joins needed
- Trade disk space for simpler code (acceptable for one-off tool)

**4. ID-Based References:**
- Entities reference each other via string IDs rather than embedded objects
- Supports JSONL streaming format (one JSON object per line)
- Python code resolves references by loading checkpoints and building lookup dictionaries

**Decisions Finalized:**
- ✅ Use LLM prompts for all fuzzy matching tasks (names, profiles, paper deduplication)
- ✅ All data models support optional fields with graceful degradation
- ✅ Track data quality issues in `data_quality_flags` per entity
- ✅ Implement models as Pydantic classes with type hints and validation

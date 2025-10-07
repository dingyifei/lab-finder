# Epic List

## Epic 1: Foundation & Configuration Infrastructure
Establish project setup, configuration management with JSON schema validation, credential handling, and user profile consolidation to create the research baseline document.

## Epic 2: University Structure Discovery & Department Filtering
Implement multi-agent department structure discovery, JSON representation for delegation, and LLM-based department relevance filtering.

## Epic 3: Professor Discovery & Filtering
Build multi-agent professor identification across filtered departments, LLM-based research field matching (ANY major field), confidence scoring, and filtered professor logging with reasoning.

## Epic 4: Lab Website Intelligence & Contact Extraction
Develop web scraping capabilities (built-in tools + Playwright fallback) to gather lab websites, member identification, and contact information extraction. **Executes in parallel with Epic 5A for 15-20% timeline reduction.**

## Epic 5A: PI Publication Research (Parallel with Epic 4)
Integrate paper-search-mcp for PI publications (3-year window), abstract and acknowledgment parsing, and journal reputation weighting. **Runs concurrently with Epic 4** to optimize pipeline performance.

## Epic 5B: Lab Member Publications & Inference
Retrieve publications for lab members identified in Epic 4, and infer lab members from co-authorship patterns when websites are unavailable or stale (using PI publications from Epic 5A).

## Epic 6: LinkedIn Integration & PhD Position Detection
Implement mcp-linkedin MCP server integration for LinkedIn profile access, LLM-based person matching with confidence scores, and graduating/departed PhD detection using configurable graduation duration.

## Epic 7: Authorship Analysis & Fitness Scoring
Build authorship pattern analysis (first/nth author), core vs. collaborator assessment, collaboration identification, and LLM-driven fitness scoring with dynamically identified criteria and weighted factors.

## Epic 8: Comprehensive Report Generation
Create comprehensive reporting system with ranked Overview.md, comparison matrix, actionable recommendations, detailed individual lab reports, and data quality flagging.

---

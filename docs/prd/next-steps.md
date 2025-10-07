# Next Steps

## UX Expert Prompt

**Note:** This project is CLI-only with no graphical user interface. UX considerations are limited to:
- CLI interaction patterns and prompts
- Progress indicator design
- Error message clarity
- Report formatting and readability

**Recommended Action:** Skip UX Expert phase or minimal review of CLI interaction design only.

---

## Architect Prompt

Please review the attached PRD (`docs/prd.md`) and create a comprehensive architecture document (`docs/architecture.md`) for the Lab Finder system.

**Key Focus Areas:**

1. **System Architecture**
   - Multi-agent orchestration design using Claude Agent SDK
   - Component breakdown and responsibilities
   - Data flow between agents and phases
   - Configuration management architecture

2. **Multi-Agent Design**
   - Agent hierarchy and delegation patterns
   - Parallel vs. sequential execution strategies
   - Batch processing coordination
   - Shared resource management (LinkedIn session queue)

3. **Data Models & Schemas**
   - JSON schema definitions for all configuration files
   - Intermediate data structures for checkpointing
   - Report output formats and templates

4. **Technical Implementation**
   - Web scraping strategy (Claude Agent SDK built-in tools + Playwright fallback)
   - MCP integration patterns (paper-search-mcp)
   - LinkedIn session management and queue implementation
   - Error handling and logging framework
   - Resumability and checkpoint/restore mechanism

5. **Key Technical Decisions**
   - Optimal batch sizes for different processing phases
   - Rate limiting strategies per data source
   - Credential storage and security approach
   - Progress tracking and reporting mechanism

**Deliverable:** Complete architecture document following the project's architecture template, ready for development handoff to the dev agent.

---


# Technical Assumptions

## Repository Structure: Monorepo

**Rationale:** Single Python project with multi-agent architecture; no need for separate repos

## Service Architecture: Monolithic Application with Multi-Agent Orchestration

**Rationale:** One-off execution tool (NFR9) with coordinated subagents; not a distributed service. The Claude Agent SDK handles agent orchestration within a single process.

## Testing Requirements: Unit + Integration Testing

**Rationale:**
- Unit tests for data processing, filtering logic, scoring algorithms
- Integration tests for web scraping workflows, MCP interactions
- Manual testing for end-to-end university analysis runs
- No continuous deployment or production users, so minimal E2E automation needed

## Additional Technical Assumptions and Requests

**Language & Framework:**
- Python 3.11+ (for modern async features)
- Claude Agent SDK (core framework per NFR1)
- Playwright for browser automation fallback (NFR5)

**Data Sources & APIs:**
- paper-search-mcp for publication retrieval (NFR6)
- Archive.org Wayback Machine API for website history (FR14)
- LinkedIn (authenticated via Playwright, NFR16)
- Configurable journal reputation database (SJR/Impact Factor) (FR17)

**Configuration Management:**
- JSON Schema for validation (FR1)
- Multiple JSON config files: user profile, university details, system parameters (FR4)
- Credential storage with CLI prompts for missing values (FR2-FR3)

**Data Persistence:**
- File-based checkpointing (JSON/JSONL) for resumability (NFR12)
- No database required - intermediate results saved to filesystem
- Report outputs: Markdown files (FR26-FR29)

**Concurrency & Performance:**
- Multi-agent architecture with configurable batch processing (NFR2, NFR4)
- MCP server integration for LinkedIn access with SDK-managed rate limiting (NFR16, NFR11)
- Configurable rate limiting per source (NFR11)
- Parallel department/professor discovery where possible

**Error Handling & Logging:**
- Detailed logging framework (NFR17)
- Graceful degradation for missing data (NFR13, FR31-FR32)
- Progress indicators for long-running operations (NFR14)

**Deployment:**
- Local execution only (one-off tool)
- No containerization required unless user requests
- Virtual environment for dependency isolation

---

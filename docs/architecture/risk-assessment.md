# Risk Assessment

This section documents architectural risks and mitigation strategies based on Claude Agent SDK validation.

## ✅ Risks Resolved

**1. Multi-Agent Orchestration Uncertainty** → RESOLVED
- **Original Risk:** Uncertainty about SDK support for hierarchical multi-agent coordination
- **Resolution:** SDK provides native AgentDefinition support for agent definition; parallel execution implemented at application-level using asyncio.gather()
- **Evidence:** Research validated AgentDefinition for agent creation; Story 3.1 v0.5 provides reference implementation for parallel execution patterns
- **Impact:** Development can proceed as planned; parallel execution achieved via application-level asyncio patterns (not SDK automatic parallelization)

**2. Web Scraping Tool Availability** → RESOLVED
- **Original Risk:** Unclear if SDK provides built-in web scraping capabilities
- **Resolution:** WebFetch and WebSearch tools confirmed as built-in
- **Evidence:** SDK documentation and research findings validate tool availability
- **Impact:** Playwright remains as fallback only; primary tooling is SDK-native

**3. MCP Integration Questions** → RESOLVED
- **Original Risk:** Uncertainty about external MCP server integration pattern
- **Resolution:** External MCP servers (paper-search-mcp, mcp-linkedin) work exactly as designed
- **Evidence:** SDK supports MCP configuration via ClaudeAgentOptions
- **Impact:** LinkedIn queue pattern simplified - MCP handles rate limiting internally

## ⚠️ Active Risks

**1. Context Isolation Complexity**

**Risk:** SDK agents maintain isolated contexts with no shared memory; all state must be passed explicitly via prompts

**Mitigation Strategies:**
- Implement robust CheckpointManager for phase-to-phase state persistence
- Include complete context in agent prompts (user profile + previous phase data)
- Use JSON serialization for structured data passing between phases
- Document context requirements in each agent's prompt template

**Impact:** Medium
- Adds prompt engineering overhead
- Requires careful checkpoint design
- Already accounted for in architecture via JSONL checkpoints

**Status:** Mitigated by checkpoint-based architecture

---

**2. WebFetch JavaScript Limitations**

**Risk:** WebFetch cannot execute JavaScript; may fail on modern JavaScript-heavy sites requiring fallback

**Mitigation Strategies:**
- Clear fallback path to Playwright defined in Web Scraping Decision Tree
- Budget for higher Playwright usage (40-60% of scraping operations)
- Accept graceful degradation - flag failed scrapes in data_quality_flags
- Playwright scripts prepared for common JS frameworks (React, Angular, Vue)

**Impact:** Low
- Already planned for in architecture (Playwright as explicit fallback)
- Does not block pipeline progression (graceful degradation strategy)
- Additional Playwright usage increases runtime but doesn't affect functionality

**Status:** Accepted risk with mitigation in place

---

**3. MCP Server Availability**

**Risk:** External MCP servers (paper-search-mcp, mcp-linkedin) may become unavailable or change APIs

**Mitigation Strategies:**
- Version pin MCP server installations in setup documentation
- Implement MCP connection health checks in Phase 0 validation
- Graceful degradation: Skip MCP-dependent features if servers unavailable
- Flag missing LinkedIn/publication data in data_quality_flags

**Impact:** Medium
- LinkedIn matching optional (can complete pipeline without it)
- Publications can be skipped (fitness scoring adapts to available data)
- User informed of missing features via data quality warnings

**Status:** Monitored - depends on external service stability

---

**4. Rate Limiting and Blocking**

**Risk:** Web scraping and LinkedIn access may trigger rate limits or account blocks

**Mitigation Strategies:**
- Implement aiolimiter for per-domain rate limiting (configurable in system_params.json)
- Use mcp-linkedin server's internal rate limiting (no application queue needed)
- Exponential backoff retry logic (tenacity library) for failed requests
- Batch processing with configurable delays between batches
- User-provided LinkedIn credentials (not shared accounts)

**Impact:** Medium
- May extend pipeline runtime if aggressive rate limits encountered
- LinkedIn blocking would disable member matching (graceful degradation)
- University blocking would require manual intervention or proxy configuration

**Status:** Mitigated by rate limiting and retry strategies

## Risk Summary

| Risk Category | Status | Mitigation | Blocking? |
|---------------|--------|------------|-----------|
| Multi-agent orchestration | ✅ Resolved | SDK native support | No |
| Web scraping tools | ✅ Resolved | WebFetch built-in | No |
| MCP integration | ✅ Resolved | SDK MCP configuration | No |
| Context isolation | ⚠️ Active | Checkpoint-based state | No |
| JavaScript limitations | ⚠️ Active | Playwright fallback | No |
| MCP server availability | ⚠️ Active | Graceful degradation | No |
| Rate limiting | ⚠️ Active | Backoff + batching | No |

**Overall Risk Level: LOW**

All critical architectural risks have been resolved through SDK validation. Active risks are manageable with defined mitigation strategies and do not block implementation.

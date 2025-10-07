# External APIs

## paper-search-mcp (MCP Server)

- **Purpose:** Retrieve academic publications for professors and lab members
- **Documentation:** https://github.com/modelcontextprotocol/servers (paper-search-mcp)
- **Base URL(s):** N/A (MCP server runs locally or as configured)
- **Authentication:** None (local MCP server)
- **Rate Limits:** Dependent on underlying search API (Semantic Scholar, arXiv, etc.)

**Key Endpoints Used:**
- MCP tool: `search_papers(query: str, year_range: tuple, max_results: int)` - Search publications by author + affiliation

**Integration Notes:**
- Configure MCP server in Claude Agent SDK config
- Query format: "author:Professor Name affiliation:University"
- Handle missing abstracts gracefully (some papers lack abstracts)
- Deduplicate results by DOI using LLM assistance

---

## mcp-linkedin (MCP Server)

- **Purpose:** Match lab members to LinkedIn profiles; retrieve education and work history
- **Documentation:** https://lobehub.com/mcp/adhikasp-mcp-linkedin
- **Repository:** https://github.com/adhikasp/mcp-linkedin
- **Base URL(s):** N/A (MCP server runs locally or as configured)
- **Authentication:** LinkedIn credentials via MCP server configuration
- **Rate Limits:** Managed internally by MCP server

**Key Tools Used:**
- `search_people(query: str, filters: dict)` - Search for LinkedIn profiles by name + affiliation
- `get_profile(profile_url: str)` - Retrieve profile details (education, experience, start dates)

**Integration Notes:**
- Configure LinkedIn credentials in MCP server settings (not in application code)
- MCP server handles session management and rate limiting automatically
- No queue needed - multiple agents can call MCP tools concurrently
- LLM-based matching of search results to lab members (name variations, affiliations)
- Handle profile access failures gracefully (private profiles, network errors)
- Fallback: Skip LinkedIn matching if MCP server unavailable; flag in data quality

---

## Archive.org Wayback Machine API

- **Purpose:** Check lab website change history and staleness
- **Documentation:** https://archive.org/help/wayback_api.php
- **Base URL(s):** `https://archive.org/wayback/available`
- **Authentication:** None (public API)
- **Rate Limits:** No official limit; respect rate limiting via aiolimiter (1 req/sec)

**Key Endpoints Used:**
- `GET /wayback/available?url={lab_url}` - Get most recent snapshot
- `GET /wayback/available?url={lab_url}&timestamp={YYYYMMDD}` - Get snapshot at specific date

**Integration Notes:**
- Not all websites are archived; handle 404s gracefully
- Use most recent snapshot date to calculate website staleness
- If current website unreachable, optionally fetch archived snapshot content

---

## Scimago Journal Rank (SJR) - Offline CSV

- **Purpose:** Assign reputation scores to publications based on journal
- **Documentation:** https://www.scimagojr.com/journalrank.php
- **Base URL(s):** Download once from https://www.scimagojr.com/journalrank.php?out=xls
- **Authentication:** None
- **Rate Limits:** N/A (static CSV download)

**Data Format:**
- CSV columns: Rank, Sourceid, Title, Type, Issn, SJR, H index, Country, Publisher
- Load into pandas DataFrame at startup
- Lookup by journal title (fuzzy match with LLM if exact match fails)

**Integration Notes:**
- Download manually and include in project data directory
- Update annually or semi-annually for latest rankings
- Handle missing journals (assign default mid-tier score or mark as unranked)

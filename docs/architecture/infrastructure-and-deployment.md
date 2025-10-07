# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** Not applicable
- **Location:** N/A
- **Approach:** No infrastructure required - local execution only

**Rationale:** As a local one-off execution tool (NFR9), Lab Finder requires no cloud infrastructure or IaC tooling.

---

## Deployment Strategy

- **Strategy:** Local Python execution via virtual environment
- **CI/CD Platform:** None (optional: GitHub Actions for tests only)
- **Pipeline Configuration:** `.github/workflows/tests.yml` (if CI enabled)

**Deployment Steps:**
1. Clone repository
2. Create Python 3.11 virtual environment: `python3.11 -m venv venv`
3. Activate environment: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Install Playwright browsers (for web scraping fallback): `playwright install`
6. Configure MCP servers:
   - Install paper-search-mcp: `npm install -g @modelcontextprotocol/server-paper-search`
   - Install mcp-linkedin: `npm install -g mcp-linkedin`
   - Configure mcp-linkedin credentials (see MCP server docs)
7. Download SJR database: `python scripts/download_sjr.py`
8. Configure application: Edit `config/*.json` files
9. Run analysis: `python src/main.py --config config/user-profile.json`

**No deployment to servers, containers, or cloud platforms required.**

---

## Environments

- **Development:** Local machine with Python 3.11 virtual environment
- **Testing:** Same as development (local execution with test fixtures)
- **Production:** Not applicable (users run locally on their own machines)

**Rationale:** Single-user, one-off execution tool has no concept of deployed environments.

---

## Environment Promotion Flow

```
Not applicable - local execution only
```

---

## Rollback Strategy

- **Primary Method:** Git version control
- **Trigger Conditions:** User discovers bugs or undesired behavior
- **Recovery Time Objective:** Immediate (checkout previous commit)

**Approach:** Users can roll back to previous versions via `git checkout <tag>` if issues arise.

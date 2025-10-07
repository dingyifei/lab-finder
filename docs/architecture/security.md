# Security

## Input Validation

- **Validation Library:** jsonschema 4.21.1 + pydantic 2.5.3
- **Validation Location:** Configuration Validator (Phase 0) before any processing
- **Required Rules:**
  - All external inputs MUST be validated against JSON schemas
  - Validation at config loading before pipeline execution
  - Whitelist approach: Only allow known config keys

---

## Authentication & Authorization

- **Auth Method:** MCP server configuration for LinkedIn authentication
- **Session Management:** Handled by mcp-linkedin MCP server
- **Required Patterns:**
  - LinkedIn credentials configured in mcp-linkedin server settings (not in application)
  - MCP server handles session management and renewal
  - Application code only calls MCP tools (no credential handling)

---

## Secrets Management

- **Development:** MCP server configuration files (outside application code)
- **Production:** Not applicable (users manage their own MCP server configs)
- **Code Requirements:**
  - NEVER hardcode credentials in source code
  - LinkedIn credentials managed by mcp-linkedin server configuration
  - No secrets in logs or error messages (mask any credentials in structlog)

---

## API Security

- **Rate Limiting:** `aiolimiter` enforces per-source rate limits
- **CORS Policy:** Not applicable (no web server)
- **Security Headers:** Not applicable (CLI tool)
- **HTTPS Enforcement:** All external API calls use HTTPS (httpx default)

---

## Data Protection

- **Encryption at Rest:** Not implemented (local files on user's machine)
- **Encryption in Transit:** HTTPS for all external API calls
- **PII Handling:**
  - User's name and resume stored locally only (never transmitted except to LLM)
  - Professor/member names are public information (no PII restrictions)
- **Logging Restrictions:**
  - Never log credentials or API keys
  - MCP servers handle credential masking internally
  - Mask sensitive fields in structured logs

---

## Dependency Security

- **Scanning Tool:** None (recommend `pip-audit` for manual checks)
- **Update Policy:** Review dependencies quarterly; update if security vulnerabilities discovered
- **Approval Process:** No formal process (single-user tool); review changes before updating

---

## Security Testing

- **SAST Tool:** None (recommend `bandit` for Python if desired)
- **DAST Tool:** Not applicable (no web service)
- **Penetration Testing:** Not applicable (local tool)

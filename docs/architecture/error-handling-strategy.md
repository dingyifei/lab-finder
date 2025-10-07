# Error Handling Strategy

## General Approach

- **Error Model:** Exception-based with graceful degradation
- **Exception Hierarchy:**
  - `LabFinderException` (base class for all custom exceptions)
    - `ConfigurationError` (invalid configs, missing credentials)
    - `WebScrapingError` (failed web requests, blocked access)
    - `LinkedInAccessError` (LinkedIn ban, session expired)
    - `MCPError` (MCP server unavailable, query failures)
    - `CheckpointError` (corrupted checkpoint files, I/O errors)
- **Error Propagation:**
  - Phase-level errors: Log, flag in data quality, continue to next phase
  - Batch-level errors: Retry batch once, then skip batch with warning
  - Item-level errors: Skip item, flag in data quality, continue batch

---

## Logging Standards

- **Library:** structlog 24.1.0
- **Format:** JSON (structured logging for parsing)
- **Levels:**
  - `DEBUG`: Detailed execution flow, LLM prompts/responses (verbose)
  - `INFO`: Phase progress, batch completion, checkpoints saved
  - `WARNING`: Missing data, skipped items, low-confidence matches
  - `ERROR`: Exceptions, failed retries, resource access failures
  - `CRITICAL`: Unrecoverable failures requiring user intervention

- **Required Context:**
  - **Correlation ID:** `correlation_id` - Generated per execution run (UUID)
  - **Phase Context:** `phase`, `batch_id`, `component` - Identifies pipeline stage
  - **User Context:** `university`, `target_department` - User's analysis target (NO PII)

**Example Log Entry:**
```json
{
  "timestamp": "2024-10-06T10:30:45Z",
  "level": "WARNING",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "phase": "professor_filter",
  "batch_id": 3,
  "component": "professor_filter_agent",
  "message": "Low confidence match for professor",
  "professor_name": "Dr. John Doe",
  "confidence_score": 68.5,
  "university": "Stanford University"
}
```

---

## Error Handling Patterns

### External API Errors

- **Retry Policy:** Exponential backoff with jitter (tenacity library)
  - Max retries: 3
  - Initial delay: 1 second
  - Backoff multiplier: 2x
  - Max delay: 10 seconds
- **Circuit Breaker:** Not implemented (one-off execution, not long-running service)
- **Timeout Configuration:**
  - Web scraping: 30 seconds per page
  - MCP queries: 60 seconds per query
  - Archive.org API: 15 seconds per request
- **Error Translation:**
  - HTTP 429 (Rate Limited) → Pause execution, wait for rate limit reset
  - HTTP 404 (Not Found) → Flag as missing data, continue
  - HTTP 403 (Forbidden) → LinkedIn ban detection, pause for user intervention
  - Network timeouts → Retry with exponential backoff

---

### Business Logic Errors

- **Custom Exceptions:**
  - `InsufficientDataError` - Not enough data to proceed with phase
  - `ValidationError` - Config validation failures (Pydantic)
  - `FilteringError` - LLM filtering returns invalid response
- **User-Facing Errors:** Rich console output with clear remediation steps
- **Error Codes:** Not implemented (use exception types directly)

---

### Data Consistency

- **Transaction Strategy:** No transactions (JSONL append-only writes are atomic)
- **Compensation Logic:** Not applicable (no distributed transactions)
- **Idempotency:**
  - Batch checkpoints are idempotent (rewriting same batch ID overwrites previous)
  - Phase restarts load existing batches and skip completed work
  - Safe to re-run entire pipeline (checkpoints prevent duplicate processing)

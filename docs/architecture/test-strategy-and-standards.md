# Test Strategy and Standards

## Testing Philosophy

- **Approach:** Test-after development (not strict TDD) with focus on critical paths
- **Coverage Goals:**
  - Unit tests: 70% code coverage minimum
  - Integration tests: Cover all external API integrations
  - Manual end-to-end: One full university analysis per release
- **Test Pyramid:**
  - 60% unit tests (models, utilities, logic)
  - 30% integration tests (MCP, web scraping, checkpoint I/O)
  - 10% manual E2E tests (full pipeline on real data)

---

## Test Types and Organization

### Unit Tests

- **Framework:** pytest 7.4.4
- **File Convention:** `tests/unit/test_<module>.py`
- **Location:** `tests/unit/`
- **Mocking Library:** pytest-mock 3.12.0
- **Coverage Requirement:** 70% minimum

**AI Agent Requirements:**
- Generate tests for all public methods and functions
- Cover edge cases: empty inputs, None values, missing fields
- Follow AAA pattern (Arrange, Act, Assert)
- Mock all external dependencies (LLM calls, web scraping, file I/O)

**Example:**
```python
def test_filter_departments_empty_list(mocker):
    # Arrange
    mock_llm = mocker.patch('src.utils.llm_helpers.analyze_relevance')
    agent = UniversityDiscoveryAgent()

    # Act
    result = agent.filter_departments([], user_profile)

    # Assert
    assert result == []
    mock_llm.assert_not_called()
```

---

### Integration Tests

- **Scope:** Test interactions between components and external services
- **Location:** `tests/integration/`
- **Test Infrastructure:**
  - **MCP Servers:** Run local paper-search-mcp and mcp-linkedin servers for tests
  - **Web Scraping:** Use mock HTML files in `tests/fixtures/`
  - **LinkedIn:** Mock MCP server responses in tests (no real LinkedIn access)
  - **File I/O:** Use temporary directories via pytest fixtures

**Example:**
```python
@pytest.mark.integration
async def test_publication_retrieval_mcp(tmp_path):
    # Arrange: MCP server running on localhost
    agent = PublicationRetrievalAgent(mcp_url="localhost:3000")

    # Act
    pubs = await agent.fetch_publications("Jane Smith", "Stanford", years=3)

    # Assert
    assert len(pubs) > 0
    assert all(pub.year >= 2021 for pub in pubs)
```

---

### End-to-End Tests

- **Framework:** Manual testing (no automated E2E)
- **Scope:** Full pipeline execution on real university data
- **Environment:** Developer's local machine with real configs
- **Test Data:** Use small university (e.g., specific department only) to limit runtime

**E2E Test Checklist:**
1. Validate configurations pass schema validation
2. University structure discovery completes
3. Professor filtering produces reasonable results
4. Publications retrieved from paper-search-mcp
5. LinkedIn matching works via mcp-linkedin (requires MCP server configured)
6. Fitness scores are calculated
7. Reports generated in `output/`
8. Checkpoint resume works after interrupt

---

## Test Data Management

- **Strategy:** Fixture-based test data for repeatable tests
- **Fixtures:** `tests/fixtures/` directory
  - `sample_config.json` - Valid configuration
  - `mock_professor_page.html` - Professor directory HTML
  - `mock_lab_website.html` - Lab website HTML
  - `sample_publications.json` - Publication data
- **Factories:** Not needed (Pydantic models with defaults serve this purpose)
- **Cleanup:** pytest `tmp_path` fixture auto-cleans temporary files

---

## Continuous Testing

- **CI Integration:** Optional GitHub Actions workflow
  - Stage 1: Linting (ruff, mypy)
  - Stage 2: Unit tests (pytest)
  - Stage 3: Integration tests (pytest with MCP server)
- **Performance Tests:** Not applicable (one-off execution)
- **Security Tests:** Credential leak detection in git pre-commit hook (optional)

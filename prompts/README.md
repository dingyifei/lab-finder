# Jinja2 Prompt Templates

This directory contains all LLM prompt templates for the Lab Finder project, externalized from the codebase for easier maintenance and version control.

## Directory Structure

```
prompts/
├── base/              # Base templates and reusable components
├── department/        # Department-related prompts
│   └── relevance_filter.j2
├── professor/         # Professor-related prompts
│   ├── research_filter.j2
│   └── name_match.j2
├── linkedin/          # LinkedIn-related prompts
│   └── profile_match.j2
└── publication/       # Publication-related prompts
    └── abstract_relevance.j2
```

## Usage

### Basic Usage

```python
from src.utils.prompt_loader import render_prompt

# Render a template with variables
prompt = render_prompt(
    "professor/research_filter.j2",
    name="Dr. Jane Smith",
    research_areas="machine learning, deep learning",
    profile="PhD student in AI",
    bio="Professor of Computer Science"
)

# Use the rendered prompt
response = await call_llm_with_retry(prompt)
```

### With Correlation IDs

```python
prompt = render_prompt(
    "department/relevance_filter.j2",
    correlation_id="dept-filter-123",
    interests="machine learning",
    degree="PhD Computer Science",
    background="BS in CS",
    department_name="Computer Science",
    school="Engineering"
)
```

## Template Format

Templates use Jinja2 syntax with the following features:

### Variable Substitution

```jinja2
Hello {{ name }}!
Your research areas: {{ research_areas }}
```

### Conditionals

```jinja2
{% if bio %}
Bio: {{ bio }}
{% else %}
Bio: Not available
{% endif %}
```

### Loops

```jinja2
{% for interest in interests %}
- {{ interest }}
{% endfor %}
```

## Coding Standards

**Rule #19:** All LLM prompts must be stored as Jinja2 templates in the `prompts/` directory. No inline prompt strings in code.

### Adding a New Template

1. **Create template file** in appropriate subdirectory:
   ```bash
   touch prompts/category/my_template.j2
   ```

2. **Write template** using Jinja2 syntax:
   ```jinja2
   Analyze this {{ entity_type }}.

   <input>
   {{ input_data }}
   </input>

   Return ONLY valid JSON:
   {"result": "value"}
   ```

3. **Use in code** via `render_prompt()`:
   ```python
   from src.utils.prompt_loader import render_prompt

   prompt = render_prompt(
       "category/my_template.j2",
       entity_type="professor",
       input_data=data
   )
   ```

4. **Add tests** in `tests/unit/test_llm_helpers.py` or `tests/unit/test_prompt_loader.py`

## Available Templates

### Department Templates

- **`department/relevance_filter.j2`**
  - Analyzes department relevance to user's research interests
  - Variables: `interests`, `degree`, `background`, `department_name`, `school`
  - Returns: JSON with `decision`, `confidence`, `reasoning`

### Professor Templates

- **`professor/research_filter.j2`**
  - Evaluates professor-user research alignment
  - Variables: `profile`, `name`, `research_areas`, `bio`
  - Returns: JSON with `confidence`, `reasoning`, `key_factors`, `confidence_explanation`

- **`professor/name_match.j2`**
  - Determines if two names refer to same person
  - Variables: `name1`, `name2`, `context`
  - Returns: JSON with `decision`, `confidence`, `reasoning`

### LinkedIn Templates

- **`linkedin/profile_match.j2`**
  - Matches LinkedIn profile to lab member
  - Variables: `member_name`, `university`, `lab_name`, `profile_data`
  - Returns: JSON with `confidence`, `reasoning`

### Publication Templates

- **`publication/abstract_relevance.j2`**
  - Rates paper abstract relevance to research interests
  - Variables: `interests`, `title`, `abstract`
  - Returns: JSON with `relevance`, `reasoning`

## Best Practices

1. **Use descriptive template names** that indicate purpose
2. **Keep templates focused** - one template per analysis task
3. **Include clear instructions** for the LLM in the template
4. **Specify exact output format** (e.g., "Return ONLY valid JSON")
5. **Document required variables** in template comments
6. **Test templates** with real data before committing
7. **Version control prompts** separately from code changes

## Jinja2 Environment Configuration

The prompt loader is configured with:
- `autoescape=False` - Templates are text, not HTML
- `trim_blocks=True` - Remove first newline after template tag
- `lstrip_blocks=True` - Strip leading spaces from start of line
- `keep_trailing_newline=True` - Preserve trailing newline

## Custom Filters

- **`strip_markdown`** - Removes markdown formatting from text
  ```jinja2
  {{ text | strip_markdown }}
  ```

## Migration Notes

**Sprint Change Proposal (2025-10-10):**
- Migrated 5 templates from `src/utils/llm_helpers.py`
- Removed ~155 lines of hardcoded prompt strings
- All tests passing (532 tests, 88% coverage)
- Zero breaking changes - templates render identical output

## Troubleshooting

### Template Not Found
```
jinja2.exceptions.TemplateNotFound: professor/my_template.j2
```
- **Solution:** Check template file exists in `prompts/professor/my_template.j2`
- **Solution:** Verify file extension is `.j2`

### Undefined Variable
```
jinja2.exceptions.UndefinedError: 'name' is undefined
```
- **Solution:** Pass all required variables to `render_prompt()`
- **Solution:** Check template for correct variable names (case-sensitive)

### Syntax Error
```
jinja2.exceptions.TemplateSyntaxError: unexpected '}'
```
- **Solution:** Check Jinja2 syntax (use `{{ }}` for variables, `{% %}` for tags)
- **Solution:** Validate template with `jinja2-cli` or online validator

## References

- **Jinja2 Documentation:** https://jinja.palletsprojects.com/
- **Project Coding Standards:** `docs/architecture/coding-standards.md`
- **Prompt Loader Implementation:** `src/utils/prompt_loader.py`
- **Test Examples:** `tests/unit/test_prompt_loader.py`

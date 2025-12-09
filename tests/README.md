# LLM Council Test Suite

Comprehensive test suite for the LLM Council project covering backend logic, storage, API endpoints, and integration scenarios.

## Running Tests

### Install Test Dependencies

```bash
# Using uv (recommended)
uv pip install -e ".[test]"

# Or using pip
pip install -e ".[test]"
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Modules

```bash
# Run only council logic tests
pytest tests/backend/test_council.py

# Run only storage tests
pytest tests/backend/test_storage.py

# Run only API endpoint tests
pytest tests/backend/test_main.py
```

### Run with Coverage

```bash
# Run tests with coverage report
pytest --cov=backend --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=backend --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Run Specific Tests

```bash
# Run a specific test class
pytest tests/backend/test_council.py::TestParseRankingFromText

# Run a specific test function
pytest tests/backend/test_council.py::TestParseRankingFromText::test_parse_numbered_format

# Run tests matching a pattern
pytest -k "ranking"
```

### Verbose Output

```bash
pytest -v
```

### See Print Statements

```bash
pytest -s
```

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and mocks
├── backend/
│   ├── test_council.py              # Core council orchestration logic
│   ├── test_openrouter.py           # OpenRouter API client
│   ├── test_agent_storage.py        # Agent CRUD operations
│   ├── test_storage.py              # Conversation storage
│   ├── test_prompt_storage.py       # Prompt management
│   └── test_main.py                 # FastAPI endpoints
└── README.md                        # This file
```

## Test Coverage Goals

- **Backend Core Logic**: >85% coverage (critical parsing and ranking logic)
- **Storage Modules**: >80% coverage
- **API Endpoints**: >75% coverage
- **Overall Backend**: >70% coverage (CI requirement)

## Key Test Areas

### 1. Ranking Parse Logic (`test_council.py`)
Critical tests for `parse_ranking_from_text()`:
- Numbered format (1. Response A)
- Plain format (Response A)
- Missing "FINAL RANKING:" header
- Malformed input
- Edge cases

### 2. Aggregate Rankings (`test_council.py`)
Tests for `calculate_aggregate_rankings()`:
- Multiple agents ranking same responses
- Tie-breaking scenarios
- Partial rankings
- Empty rankings

### 3. Storage Operations
Tests for data persistence:
- CRUD operations
- File I/O error handling
- Corrupted JSON handling
- Concurrent access scenarios

### 4. API Client (`test_openrouter.py`)
Tests for OpenRouter integration:
- Successful queries
- HTTP error handling
- Timeout handling
- Network failures
- Malformed responses

### 5. API Endpoints (`test_main.py`)
Tests for FastAPI endpoints:
- Request validation
- Error responses (404, 422)
- CORS headers
- Full conversation flow

## Fixtures

Shared fixtures are defined in `conftest.py`:

- `temp_data_dir`: Temporary directory for test data
- `sample_agent`: Single agent configuration
- `sample_agents`: Multiple agent configurations
- `sample_conversation`: Sample conversation data
- `mock_openrouter_response`: Mocked API response
- `mock_openrouter_client`: Mocked httpx client
- `sample_stage1_results`: Sample stage 1 results
- `sample_ranking_text_*`: Various ranking text formats

## Mocking Strategy

Tests use mocking to avoid:
- Real API calls to OpenRouter (costly and slow)
- File system operations (isolated using temp directories)
- Network I/O (mocked with httpx-mock/respx)

## Continuous Integration

Tests run automatically on every commit via GitHub Actions (`.github/workflows/test.yml`).

The CI pipeline includes:
1. Backend tests with coverage
2. Frontend linting and build
3. Integration tests
4. Code quality checks
5. Coverage threshold enforcement (70% minimum)

## Writing New Tests

When adding new tests:

1. **Use descriptive test names**: `test_what_is_tested_and_expected_outcome`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Use appropriate fixtures**: Leverage existing fixtures from `conftest.py`
4. **Mock external dependencies**: Don't make real API calls or network requests
5. **Test edge cases**: Empty inputs, None values, malformed data
6. **Test error paths**: Not just happy paths

Example:

```python
def test_parse_empty_ranking_text():
    """Test that empty ranking text returns empty list."""
    # Arrange
    ranking_text = ""

    # Act
    result = parse_ranking_from_text(ranking_text)

    # Assert
    assert result == []
```

## Debugging Failed Tests

```bash
# Run with verbose output and show print statements
pytest -vvs

# Run only failed tests from last run
pytest --lf

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l
```

## Performance

Current test suite performance:
- **Backend tests**: ~5-10 seconds
- **Coverage report generation**: ~2 seconds

To identify slow tests:
```bash
pytest --durations=10
```

## Future Improvements

- [ ] Add frontend component tests (Vitest + React Testing Library)
- [ ] Add end-to-end tests (Playwright)
- [ ] Add load/stress tests
- [ ] Add mutation testing (mutmut)
- [ ] Add contract tests for API
- [ ] Increase coverage to >85% backend

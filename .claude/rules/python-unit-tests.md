# Python Unit Test Generation Rules

Apply these rules when generating or modifying unit tests in this project.

## Framework & Dependencies

- **pytest** as testing framework
- **pytest-cov** for coverage
- **pytest-mock** for mocking (`mocker` fixture)
- **In-memory SQLite** for database tests (not mocked queries)

## Structure Requirements

- **Standalone functions** - no test classes
- **Parametrize** - use `pytest.mark.parametrize` with `pytest.param` and descriptive `id` values
- **Naming**: `test_<function_name>_<scenario>`
- **Limit**: 2-3 test cases per category

## Test Categories (Generate All Applicable)

1. **Happy Flow**: Normal execution with valid inputs
2. **Edge Cases**: Boundary conditions, empty inputs, None values
3. **Exceptions**: Invalid inputs that should raise errors
4. **Interactions** (when relevant): Verify method calls, side effects

## Database Testing

- Use `db_session` fixture from `tests/conftest.py` (creates in-memory SQLite)
- Use factory functions from conftest: `create_account()`, `create_transaction()`, `create_category_mapping()`, etc.
- Test real queries - don't mock SQLAlchemy

## Mocking Rules

- Use `mocker` fixture (pytest-mock) for external dependencies
- Mock: external APIs, file systems, time-dependent operations
- Don't mock: SQLAlchemy queries, internal service calls
- **Naming**:
  - Fixture names: `mock_` prefix (e.g., `mock_api_client`)
  - Mock variables: `mocked_` prefix (e.g., `mocked_response`)

## Fixture Reuse

- Check `tests/conftest.py` for existing fixtures before creating new ones
- Create fixtures for mocks used across multiple tests
- Keep test data minimal and focused

## Test File Template

```python
import pytest
from datetime import date

from services.example_service import ExampleService
from tests.conftest import create_account, create_transaction


@pytest.fixture
def example_service(db_session):
    """Service instance with test database session."""
    return ExampleService(session=db_session)


# ==================== Happy Flow ====================

@pytest.mark.parametrize("input_val,expected", [
    pytest.param("valid_input", "expected_output", id="basic_case"),
    pytest.param("another_valid", "another_expected", id="alternate_case"),
])
def test_method_name_happy_flow(db_session, example_service, input_val, expected):
    """Should return expected result for valid inputs."""
    result = example_service.method_name(input_val)
    assert result == expected


# ==================== Edge Cases ====================

@pytest.mark.parametrize("edge_input,expected", [
    pytest.param(None, None, id="none_input"),
    pytest.param("", None, id="empty_string"),
    pytest.param([], [], id="empty_list"),
])
def test_method_name_edge_cases(example_service, edge_input, expected):
    """Should handle edge cases gracefully."""
    result = example_service.method_name(edge_input)
    assert result == expected


# ==================== Exceptions ====================

@pytest.mark.parametrize("invalid_input,exception_type", [
    pytest.param(-1, ValueError, id="negative_number"),
    pytest.param("invalid", TypeError, id="wrong_type"),
])
def test_method_name_exceptions(example_service, invalid_input, exception_type):
    """Should raise appropriate exceptions for invalid inputs."""
    with pytest.raises(exception_type):
        example_service.method_name(invalid_input)
```

## Running Tests

```bash
pytest                                    # All tests
pytest --cov=services                     # With coverage
pytest tests/services/test_example.py    # Specific file
pytest -k "test_normalize"               # By name pattern
pytest -v                                 # Verbose output
```
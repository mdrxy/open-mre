# Global Development Guidelines for LangChain Projects

## Core Development Principles

### Code Quality Standards

**All Python code MUST include type hints and return types.**

❌ **Bad:**

```python
def p(u, d):
    return [x for x in u if x not in d]
```

✅ **Good:**

```python
def filter_unknown_users(users: list[str], known_users: set[str]) -> list[str]:
    """Filter out users that are not in the known users set.

    Args:
        users: List of user identifiers to filter.
        known_users: Set of known/valid user identifiers.

    Returns:
        List of users that are not in the known_users set.
    """
    return [user for user in users if user not in known_users]
```

**Style Requirements:**

- Use descriptive, **self-explanatory variable names**. Avoid overly short or cryptic identifiers.
- Attempt to break up complex functions (>20 lines) into smaller, focused functions where it makes sense
- Avoid unnecessary abstraction or premature optimization
- Follow existing patterns in the codebase you're modifying

### 3. Testing Requirements

**Every new feature or bugfix MUST be covered by unit tests.**

**Test Organization:**

- Unit tests: `tests/unit_tests/` (no network calls allowed)
- Integration tests: `tests/integration_tests/` (network calls permitted)
- Use `pytest` as the testing framework

**Test Quality Checklist:**

- [ ] Tests fail when your new logic is broken
- [ ] Happy path is covered
- [ ] Edge cases and error conditions are tested
- [ ] Use fixtures/mocks for external dependencies
- [ ] Tests are deterministic (no flaky tests)

Checklist questions:

- [ ] Does the test suite fail if your new logic is broken?
- [ ] Are all expected behaviors exercised (happy path, invalid input, etc)?
- [ ] Do tests use fixtures or mocks where needed?

```python
def test_filter_unknown_users():
    """Test filtering unknown users from a list."""
    users = ["alice", "bob", "charlie"]
    known_users = {"alice", "bob"}

    result = filter_unknown_users(users, known_users)

    assert result == ["charlie"]
    assert len(result) == 1
```

### 4. Security and Risk Assessment

**Security Checklist:**

- No `eval()`, `exec()`, or `pickle` on user-controlled input
- Proper exception handling (no bare `except:`) and use a `msg` variable for error messages
- Remove unreachable/commented code before committing
- Race conditions or resource leaks (file handles, sockets, threads).
- Ensure proper resource cleanup (file handles, connections)

❌ **Bad:**

```python
def load_config(path):
    with open(path) as f:
        return eval(f.read())  # ⚠️ Never eval config
```

✅ **Good:**

```python
import json

def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)
```

### 5. Documentation Standards

**Use Google-style docstrings with Args section for all public functions.**

❌ **Insufficient Documentation:**

```python
def send_email(to, msg):
    """Send an email to a recipient."""
```

✅ **Complete Documentation:**

```python
def send_email(to: str, msg: str, *, priority: str = "normal") -> bool:
    """
    Send an email to a recipient with specified priority.

    Args:
        to: The email address of the recipient.
        msg: The message body to send.
        priority: Email priority level (`'low'`, `'normal'`, `'high'`).

    Returns:
        `True` if email was sent successfully, `False` otherwise.

    Raises:
        `InvalidEmailError`: If the email address format is invalid.
        `SMTPConnectionError`: If unable to connect to email server.
    """
```

**Documentation Guidelines:**

- Types go in function signatures, NOT in docstrings
  - If a default is present, DO NOT repeat it in the docstring unless there is post-processing or it is set conditionally.
- Focus on "why" rather than "what" in descriptions
- Document all parameters, return values, and exceptions
- Keep descriptions concise but clear
- Ensure American English spelling (e.g., "behavior", not "behaviour")

### 6. Architectural Improvements

**When you encounter code that could be improved, suggest better designs:**

❌ **Poor Design:**

```python
def process_data(data, db_conn, email_client, logger):
    # Function doing too many things
    validated = validate_data(data)
    result = db_conn.save(validated)
    email_client.send_notification(result)
    logger.log(f"Processed {len(data)} items")
    return result
```

✅ **Better Design:**

```python
@dataclass
class ProcessingResult:
    """Result of data processing operation."""
    items_processed: int
    success: bool
    errors: List[str] = field(default_factory=list)

class DataProcessor:
    """Handles data validation, storage, and notification."""

    def __init__(self, db_conn: Database, email_client: EmailClient):
        self.db = db_conn
        self.email = email_client

    def process(self, data: List[dict]) -> ProcessingResult:
        """Process and store data with notifications."""
        validated = self._validate_data(data)
        result = self.db.save(validated)
        self._notify_completion(result)
        return result
```

**Design Improvement Areas:**

If there's a **cleaner**, **more scalable**, or **simpler** design, highlight it and suggest improvements that would:

- Reduce code duplication through shared utilities
- Make unit testing easier
- Improve separation of concerns (single responsibility)
- Make unit testing easier through dependency injection
- Add clarity without adding complexity
- Prefer dataclasses for structured data

## Development Tools & Commands

### Package Management

```bash
# Add package
uv add package-name

# Sync project dependencies
uv sync
uv lock
```

### Testing

```bash
# Run unit tests (no network)
make test

# Don't run integration tests, as API keys must be set

# Run specific test file
uv run --group test pytest tests/unit_tests/test_specific.py
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type checking
uv run --group lint mypy .
```

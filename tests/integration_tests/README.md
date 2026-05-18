# Integration Tests Needed

This document outlines the key integration tests required for Open-MRE.

## 1. Full Graph E2E Flow

**File:** `test_coordinator_full_workflow.py`

| Test Case | Description |
|-----------|-------------|
| `test_valid_issue_full_workflow` | Run complete graph with valid issue fixture, verify all nodes execute |
| `test_invalid_issue_early_termination` | Run with invalid issue, verify early termination and draft comments |
| `test_no_execute_flag_skips_executor` | Run with `--no-execute` flag, verify executor is skipped |
| `test_state_propagation_between_nodes` | Verify state propagates correctly between all 6 nodes |

## 2. Daytona Sandbox Execution

**File:** `test_daytona_sandbox.py`

| Test Case | Description |
|-----------|-------------|
| `test_workspace_lifecycle` | Create workspace → install packages → execute code → cleanup |
| `test_environment_variables_passed` | Verify env vars are correctly injected into sandbox |
| `test_execution_timeout` | Code that runs too long is terminated gracefully |
| `test_error_capture` | Code that raises exceptions has stderr captured |
| `test_workspace_cleanup_on_failure` | Workspace is cleaned up even when execution fails |

> Requires: `DAYTONA_API_KEY` environment variable

## 3. Agent Subgraph Tests

### Version Validator

**File:** `test_version_validator_integration.py`

| Test Case | Description |
|-----------|-------------|
| `test_pypi_live_api` | Real PyPI API calls (not mocked) |
| `test_outdated_package_detection` | Verify outdated package detection with live data |

### Code Extractor

**File:** `test_code_extractor_integration.py`

| Test Case | Description |
|-----------|-------------|
| `test_extract_fenced_code` | Extract code from markdown fenced blocks |
| `test_extract_unfenced_code` | LLM identifies unfenced code snippets |
| `test_complex_markdown_extraction` | Handle real-world issue formatting |

### Executor

**File:** `test_executor_integration.py`

| Test Case | Description |
|-----------|-------------|
| `test_code_hydration_with_llm` | LLM adds necessary imports/boilerplate |
| `test_sandbox_execution_with_packages` | Install packages and run code end-to-end |

## 4. HITL Interrupt/Resume

**File:** `test_api_key_approval_flow.py`

| Test Case | Description |
|-----------|-------------|
| `test_graph_pauses_when_keys_needed` | Graph pauses at `api_key_check` node |
| `test_resume_with_approval` | Resume with approval → executor runs |
| `test_resume_with_rejection` | Resume with rejection → executor skipped |

## 5. Output Generation

**File:** `test_output_files.py`

| Test Case | Description |
|-----------|-------------|
| `test_validation_report_structure` | `validation_report.md` contains expected sections |
| `test_reproduction_script_valid_python` | `reproduction.py` is syntactically valid Python |
| `test_draft_comments_formatting` | `draft_comments.md` formatted correctly |

---

## Running Integration Tests

```bash
# Run all integration tests (requires API keys)
uv run pytest tests/integration_tests/ -v

# Run with specific markers
uv run pytest tests/integration_tests/ -m "not slow" -v
```

## Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `DAYTONA_API_KEY` | Sandbox execution |
| `ANTHROPIC_API_KEY` | LLM calls for agents |
| `LANGSMITH_API_KEY` | Tracing (optional) |

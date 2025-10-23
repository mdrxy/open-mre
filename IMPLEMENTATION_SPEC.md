# open-MRE Implementation Specification

## Project Overview

**open-MRE** is an automated system for validating Minimal Reproducible Examples (MREs) from bug reports. It receives markdown issue reports, extracts and executes the code, and produces either a runnable, validated reproduction or requests additional context from the author.

### Technology Stack

- **Framework**: [Deep Agents](https://github.com/langchain-ai/deepagents) (LangChain and LangGraph-based agent orchestration)
- **Language Support**: Python
- **Code Execution**: Provider tools (Claude/OpenAI Code Execution) or Daytona Sandbox
- **Architecture**: Coordinator agent with specialized subagents

---

## System Architecture

### High-Level Flow

```txt
Input: issue.md (bug report with code)
    ↓
[Coordinator Agent]
    ├─→ [Code Extraction Subagent] → extracted code + metadata
    ├─→ [Version Validation Subagent] → version status report
    ├─→ [Behavior Analysis Subagent] → expected vs actual behavior
    ├─→ [Execution Subagent] → execution results + captured output
    └─→ [Report Generator Subagent] → final report + `.py` file (if successful)
    ↓
Output: `validation_report.md` + `reproduction.py` (if successful)
```

### Agent Hierarchy

1. **Coordinator Agent** (`mre_coordinator`)
   - Orchestrates the validation workflow
   - Uses `write_todos` to break down validation process
   - Delegates tasks to subagents
   - Aggregates results and determines final outcome

2. **Subagents** (5 specialized agents)
   - `code_extractor`: Parse markdown, extract code blocks
   - `version_validator`: Check package versions mentioned in issue against PyPI latest
   - `behavior_analyst`: Parse expected/actual behavior
   - `executor`: Run code in isolated environment
   - `report_generator`: Generate final reports

---

## Detailed Component Specifications

### 1. Coordinator Agent

**Responsibilities**:

- Receive markdown issue file path as input
- Use `write_todos` to plan validation steps:
  1. Extract code from issue
  2. Validate package versions
  3. Analyze expected behavior
  4. Execute code and capture output
  5. Generate final report
- Delegate each step to appropriate subagent using `task` tool
- Aggregate all subagent outputs
- Determine final outcome (green/yellow/red flag)

**System Prompt Template**:

```text
You are the MRE Validation Coordinator. Your job is to validate bug reports by:

1. First, use write_todos to break down the validation process into steps
2. Delegate tasks to specialized subagents using the task tool
3. Aggregate results from all subagents
4. Determine the final validation outcome:
   - GREEN FLAG: Issue successfully reproduced
   - YELLOW FLAG: Partial reproduction or unclear results
   - RED FLAG: Cannot reproduce or missing information

Always start by reading the issue file, then create a todo list for the validation steps.
```

**Tools**:

- `read_file`: Read input markdown file
- `write_todos`: Plan validation steps
- `task`: Delegate to subagents
- `write_file`: Write final outputs

**Subagents**:

- All 5 subagents listed below

---

### 2. Code Extractor Subagent

**Name**: `code_extractor`

**Description**:

```txt
Extracts Python code blocks from markdown issue files. Identifies code blocks, adds missing context (imports, entrypoints), and hydrates incomplete code/placeholders with samples.

Returns structured code ready for execution. Hydration should not change original logic.
```

**System Prompt**:

```txt
You are a Python code extraction specialist. Given a markdown bug report:

1. Extract all code blocks
2. Identify missing imports and add them (use common library patterns, refer the the `langchain`, langchain_core`, and `langgraph` library files as needed)
3. Add a main entrypoint if missing (e.g., ``if __name__ == "__main__":``)
4. DO NOT assume user intent - only add obviously missing boilerplate
5. Preserve original code logic exactly as provided
6. Write extracted code to `/extracted_code.py`
7. Write metadata to `/extraction_metadata.json` with:
   - `code_blocks_found`: int
   - `imports_added`: list[str]
   - `entrypoint_added`: bool
   - `warnings`: list[str] (if code is incomplete)

Return a summary of what was extracted and any concerns.
```

**Tools**:

- `read_file`: Read markdown issue
- `write_file`: Write extracted code and metadata

**Input**: Path to markdown file (via task description)

**Output**:

- `/extracted_code.py`: Runnable Python file
- `/extraction_metadata.json`: Extraction details
- Summary message with warnings

---

### 3. Version Validator Subagent

**Name**: `version_validator`

**Description**:

```txt
Validates that mentioned package versions are latest. Extracts package names and versions from issue, queries PyPI API, and returns version status report.
```

In the implementation of this part, it may be worth using another subagent that uses provider-strategy structure output, where we provide it a schema. See: <https://docs.langchain.com/oss/python/langchain/models#structured-outputs>

**System Prompt**:

```txt
You are a Python package version validator. Given a bug report:

1. Extract all mentioned packages and versions (e.g., "pandas 2.0.0", "numpy>=1.24")
2. For each package, check if version is latest using PyPI API
3. If no version mentioned, assume user is using latest
4. Write results to `/version_report.json` with JSON structure:

   {
     "packages": [
       {
         "name": "package_name",
         "mentioned_version": "1.0.0" | null,
         "latest_version": "1.2.0",
         "is_latest": false,
         "needs_update": true
       }
     ],
     "all_latest": false,
     "can_proceed": true  // false only if critical version mismatch
   }

Return summary of version validation results.
```

**Tools**:

- `read_file`: Read markdown issue
- `check_pypi_version`: Custom tool (see below)
- `write_file`: Write version report

**Custom Tool Required**:

```python
@tool
def check_pypi_version(package_name: str) -> dict[str, str]:
    """
    Query PyPI JSON API to get latest version of a package.

    Args:
        package_name: Name of Python package (e.g., `'requests'`)

    Returns:
        `{"package": "requests", "latest_version": "2.31.0", "error": null}`
    """
```

**Output**:

- `/version_report.json`: Version validation results
- Summary message
- If the versions are outdated, flag `can_proceed: false` if critical so that we end agent execution and jump to report generation.

---

### 4. Behavior Analyst Subagent

**Name**: `behavior_analyst`

**Description**:

```txt
Parses expected and actual behavior from bug reports. Creates structured comparison criteria for validation.
```

**System Prompt**:

```txt
You are a behavior analysis specialist. Given a bug report:

1. Extract the EXPECTED behavior:
   - Look for sections like "Expected behavior", "Should do", etc.
   - Parse error messages, return values, or outcomes described

2. Extract the ACTUAL behavior (if provided):
   - Look for sections like "Actual behavior", "What happens", etc.

3. Create comparison criteria:
   - If expected is an error: check if error type/message matches
   - If expected is output: check if output contains/matches description
   - If expected is behavior: describe what to validate

4. Write to `/behavior_analysis.json`:
   {
     "expected_behavior": {
       "type": "error" | "output" | "state_change",
       "description": "...",
       "validation_criteria": "..."
     },
     "actual_behavior": {
       "description": "...",
       "provided": true
     },
     "comparison_strategy": "exact_match" | "contains" | "pattern_match"
   }

5. If expected behavior is unclear or missing, set flag `needs_clarification: true`

Return structured behavior analysis.
```

**Tools**:

- `read_file`: Read markdown issue
- `write_file`: Write behavior analysis

**Output**:

- `/behavior_analysis.json`: Structured behavior expectations
- Summary message (with warning if behavior unclear)

---

### 5. Executor Subagent

**Name**: `executor`

**Description**:

```txt
Executes extracted Python code in an isolated environment. Captures stdout, stderr, and return codes. Handles timeouts and errors gracefully.
```

**System Prompt**:

```txt
You are a code execution specialist. Your job:

1. Read the extracted code from `/extracted_code.py`
2. Read the version report from `/version_report.json` - get the `latest_version` of each package
3. Install required packages before execution
4. Execute the code using the provided code execution tool
5. Capture all output: stdout, stderr, exceptions, return code
6. Handle execution gracefully:
   - Set timeout to 30 seconds
   - Catch all exceptions and record them
   - If code requires user input, mark as "needs_interaction"
7. Write results to `/execution_results.json`:
   {
     "exit_code": 0,
     "stdout": "...",
     "stderr": "...",
     "exception": "..." | null,
     "timed_out": false,
     "needs_interaction": false,
     "execution_time_ms": 1234
   }

Return execution summary with key findings.
```

**Tools**:

- `read_file`: Read extracted code and version report
- `execute_python_code`: Custom tool (see below)
- `write_file`: Write execution results

**Custom Tool Required**:

We need to decide what is better for the MVP here;

**Option A: Claude Code Execution Tool**

```python
@tool
def execute_python_code(code: str, packages: list[str]) -> dict:
    """
    Execute Python code using Claude's code execution tool.
    See: https://docs.claude.com/en/docs/agents-and-tools/tool-use/code-execution-tool
    """
```

**Option B: OpenAI Code Interpreter**

```python
@tool
def execute_python_code(code: str, packages: list[str]) -> dict:
    """
    Execute Python code using OpenAI's code interpreter.
    See: https://platform.openai.com/docs/guides/tools-code-interpreter
    """
```

**Option C: Daytona Sandbox**

```python
@tool
def execute_python_code(code: str, packages: list[str]) -> dict:
    """
    Execute Python code in Daytona sandbox.
    See: https://www.daytona.io/
    """
```

**Output**:

- `/execution_results.json`: Execution outcomes
- Summary message

---

### 6. Report Generator Subagent

**Name**: `report_generator`

**Description**:

```txt
Generates final validation reports. Creates runnable `.py` file if reproduction successful, or requests for additional context if failed.
```

**System Prompt**:

```txt
You are the final report generator. Aggregate all results and create outputs:

1. Read all generated files:
   - `/extraction_metadata.json`
   - `/version_report.json`
   - `/behavior_analysis.json`
   - `/execution_results.json`

2. Compare execution results with expected behavior:
   - Match error types/messages
   - Check output against expectations
   - Determine if issue is reproduced

3. Determine outcome flag:
   - GREEN FLAG: Issue successfully reproduced
     - Execution matches expected behavior
     - All versions are latest (or as specified)
   - YELLOW FLAG: Partial reproduction
     - Code runs but behavior doesn't match exactly
     - Version mismatch but issue still occurs
   - RED FLAG: Cannot reproduce
     - Code doesn't run as described
     - Missing critical information
     - Need more context from user

4. Generate outputs:

   A. If GREEN FLAG:
      - Write `/reproduction.py` (copy from `extracted_code.py`)
        - We should make sure the file actually compiles without error
      - Write `/validation_report.md` with:
        - Status: REPRODUCED
        - Summary of issue
        - Execution results
        - Package versions used
        - Steps to reproduce

   B. If YELLOW FLAG:
      - Write `/validation_report.md` with:
        - Status: PARTIAL_REPRODUCTION
        - What worked vs. what didn't
        - Request for specific clarifications
        - Execution diff

   C. If RED FLAG:
      - Write `/validation_report.md` with:
        - Status: CANNOT_REPRODUCE
        - What was attempted
        - Specific questions for issue author
        - Missing information needed

Return final status and summary.
```

**Tools**:

- `read_file`: Read all previous outputs
- `write_file`: Write report and .py file

**Output**:

- `/validation_report.md`: Final report
- `/reproduction.py`: Runnable code (if GREEN flag)
- Summary message with final status

---

## Output Specifications

### Validation Report (`validation_report.md`)

**GREEN FLAG Example**:

```markdown
# MRE Validation Report

**Status**: ✓ REPRODUCED

## Summary
Successfully reproduced the reported issue with provided code.

## Execution Results
- Exit code: 0
- Exception: ValueError: cannot convert float NaN to integer
- Execution time: 245ms

## Package Versions
- pandas: 2.1.3 (latest)
- numpy: 1.26.0 (latest)

## Reproduction File
Validated code written to: `reproduction.py`

## Notes
Issue reproduced exactly as described. The error occurs when attempting to convert
a DataFrame with NaN values to integer type.
```

**YELLOW FLAG Example**:

```markdown
# MRE Validation Report

**Status**: ⚠ PARTIAL_REPRODUCTION

## Summary
Code executes but behavior differs from description.

## Discrepancies
- Expected: ValueError
- Actual: TypeError: unsupported operand type(s) for +: 'int' and 'str'

## Questions for Issue Author
1. Are you using a different version of pandas? (you mentioned 2.0.0, latest is 2.1.3)
2. Can you confirm the input data types?
3. Is there additional setup code we're missing?

## Execution Details
[... execution results ...]
```

**RED FLAG Example**:

```markdown
# MRE Validation Report

**Status**: ✗ CANNOT_REPRODUCE

## Summary
Unable to reproduce issue - missing critical information.

## Issues Identified
1. No code provided in issue report
2. Expected behavior not clearly described
3. Package versions not specified

## Request for Additional Information
To validate this issue, please provide:

1. **Minimal code example** that demonstrates the problem
2. **Exact error message** or unexpected output
3. **Package versions**: Run `pip list` and include relevant versions
4. **Python version**: Output of `python --version`

## Attempted Steps
- Attempted to generate sample code based on description
- Could not determine root cause without executable example
```

#### Reproduction File (reproduction.py)

Only created for GREEN FLAG outcomes:

```python
"""
MRE Validation - Issue #123
Successfully reproduced on: 2025-10-23
Python: 3.11 | pandas: 2.1.3 | numpy: 1.26.0

Original issue: [link if available]
"""

import pandas as pd
import numpy as np

def reproduce_issue():
    # Code that reproduces the issue
    df = pd.DataFrame({'col': [1, 2, np.nan]})

    # This triggers the reported error
    df['col'].astype(int)  # ValueError: cannot convert float NaN to integer

if __name__ == "__main__":
    reproduce_issue()
```

---

## Implementation Guidelines

### File Structure

```txt
open-mre/
├── open_mre/
│   ├── __init__.py
│   ├── coordinator.py
│   ├── subagents/
│   ├── tools/
│   └── main.py
├── tests/
│   ├── fixtures/
│   │   ├── valid_issue.md
│   │   ├── partial_issue.md
│   │   └── invalid_issue.md
│   └── test_coordinator.py
├── pyproject.toml
├── Makefile # (format/lint/test)
└── README.md
```

### Creating the Coordinator Agent

```python
from deepagents import create_deep_agent
from open_mre.subagents import (
    ...
)

COORDINATOR_PROMPT = """..."""

def create_mre_coordinator():
    return create_deep_agent(
        name="mre_coordinator",
        system_prompt=COORDINATOR_PROMPT,
        subagents=[
            code_extractor_subagent,
            version_validator_subagent,
            behavior_analyst_subagent,
            executor_subagent,
            report_generator_subagent,
        ],
        tools=[],  # Coordinator only needs default tools (read/write_file, task, write_todos)
    )
```

### Example Subagent Definition

```python
# src/open_mre/subagents/code_extractor.py

from open_mre.tools import extract_code_blocks, add_missing_imports

CODE_EXTRACTOR_PROMPT = """
...
"""

code_extractor_subagent = {
    "name": "code_extractor",
    "description": (
        "Extracts Python code blocks from markdown issue files. Identifies code blocks, "
        "adds missing context (imports, entrypoints), and hydrates incomplete code."
    ),
    "system_prompt": CODE_EXTRACTOR_PROMPT,
    "tools": [extract_code_blocks, add_missing_imports],
}
```

### CLI Entry Point

```python
# src/open_mre/main.py

import sys
from pathlib import Path
from langchain_core.messages import HumanMessage
from open_mre.coordinator import create_mre_coordinator

def main():
    if len(sys.argv) != 2:
        print("Usage: open-mre <issue.md>")
        sys.exit(1)

    issue_path = Path(sys.argv[1])
    if not issue_path.exists():
        print(f"Error: File not found: {issue_path}")
        sys.exit(1)

    # Create coordinator agent
    coordinator = create_mre_coordinator()

    # Run validation
    task = f"Validate the bug report at {issue_path.absolute()}. Follow the full MRE validation workflow."
    result = coordinator.invoke({
        "messages": [HumanMessage(content=task)]
    })

    # Print final result
    final_message = result["messages"][-1].content
    print(final_message)

    # Check for output files
    if Path("validation_report.md").exists():
        print("\n✓ Validation report written to: validation_report.md")
    if Path("reproduction.py").exists():
        print("✓ Reproduction script written to: reproduction.py")

if __name__ == "__main__":
    main()
```

---

## Custom Tools Implementation

### PyPI Version Checker

```python
# src/open_mre/tools/pypi_checker.py

import httpx
from langchain_core.tools import tool

@tool
def check_pypi_version(package_name: str) -> dict[str, str | None]:
    """
    Query PyPI JSON API to get latest version of a package.

    Args:
        package_name: Name of Python package (e.g., "requests")

    Returns:
        {"package": "requests", "latest_version": "2.31.0", "error": null}
    """
    try:
        response = httpx.get(f"https://pypi.org/pypi/{package_name}/json", timeout=5.0)
        response.raise_for_status()
        data = response.json()
        return {
            "package": package_name,
            "latest_version": data["info"]["version"],
            "error": None,
        }
    except Exception as e:
        return {
            "package": package_name,
            "latest_version": None,
            "error": str(e),
        }
```

---

## Testing Strategy

### Unit Tests

- Test each subagent independently with mock inputs
- Test custom tools (PyPI checker, code executor)
- Validate JSON schema outputs

### Integration Tests

Test cases from real issues will be provided.

---

## Error Handling & Edge Cases

### Edge Cases to Handle

1. **Multiple Code Blocks**: Extract all, attempt to combine into single script
2. **Missing Imports**: Add common imports (pandas, numpy, requests, etc.)
3. **Incomplete Code**: Flag as warning, attempt basic completion
4. **Interactive Code**: Detect `input()` calls, flag as needs_interaction
5. **Long-Running Code**: 30-second timeout, report timeout error
6. **Relative Imports**: Convert to absolute imports when possible
7. **File Dependencies**: Flag if code references external files
8. **Network Requests**: Allow but log as potential flakiness source

### Error Messages

All subagents should handle errors gracefully and return structured error info:

```json
{
  "success": false,
  "error": "SubagentError",
  "message": "Failed to extract code: no code blocks found",
  "recovery_suggestion": "Request user to provide code in markdown code blocks"
}
```

## Questions

When implementing this specification, clarify:

1. **Code execution provider**: Which should we use first?
   - Claude Code Execution (requires Anthropic API)
   - OpenAI Code Interpreter (requires OpenAI API)
   - Daytona Sandbox (requires Daytona account)
   - Custom subprocess (works immediately but less secure)

2. **State persistence**: Should validation history be stored?
   - Use LangGraph checkpointer for resumability
   - Store results in database for analytics
   - Just write to local filesystem

3. **Error recovery**: How aggressive should retry logic be?
   - Retry on transient failures (network, timeouts)
   - Don't retry on deterministic failures (syntax errors)

4. **Output location**: Where should validation outputs be written?
   - Same directory as input issue.md
   - Dedicated output directory (./validations/)
   - Temporary directory (deleted after reporting)

---

## Contact & Support

For questions during implementation:

- Review deepagents examples: `/Users/mdrxy/oss/deepagents/examples/`
- Check deepagents docs: [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) or use the MCP tool
  - <https://docs.langchain.com/oss/python/deepagents/subagents>
  - <https://docs.langchain.com/oss/python/deepagents/customization>
  - <https://reference.langchain.com/python/deepagents/>
- Reference this spec: `IMPLEMENTATION_SPEC.md`

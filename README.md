# `open-mre`

Automated system for validating Minimal Reproducible Examples (MREs) from bug reports.

## Overview

`open-mre` receives markdown issue reports, extracts and executes the code, and produces either a runnable, validated reproduction or requests additional context from the author.

## Technology Stack

- **Framework**: [Deep Agents](https://github.com/langchain-ai/deepagents) (LangChain and LangGraph-based agent orchestration)
- **Code Execution**: Provider tools (Claude/OpenAI Code Execution)
- **Architecture**: Coordinator agent with specialized subagents

## Usage

```bash
open-mre path/to/issue.md
```

This will:

1. Extract code from the bug report
2. Validate package versions
3. Execute the code
4. Generate a validation report

## Output

- `validation_report.md`: Validation results with status (GREEN/YELLOW/RED)
- `reproduction.py`: Runnable reproduction script (if successful)

## Architecture

The system uses a coordinator agent that delegates to five specialized subagents:

1. **Code Extractor**: Extracts Python code from markdown
2. **Version Validator**: Checks package versions against PyPI
3. **Behavior Analyst**: Parses expected vs actual behavior
4. **Executor**: Runs code in isolated environment
5. **Report Generator**: Creates final validation reports

See `IMPLEMENTATION_SPEC.md` for detailed technical specifications.

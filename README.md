# `open-mre`

[Deep agent](https://docs.langchain.com/oss/python/deepagents/overview) used to validate Minimal Reproducible Examples (MREs) from incoming issues.

## Overview

`open-mre` receives bug reports, extracts and executes the MRE, and produces either a runnable, validated reproduction (w/ batteries included) for maintainers, or requests additional context from the author. See the [design doc](./IMPLEMENTATION_SPEC.md) for more details and the [architecture section](#architecture).

## Stack

- [Deep Agents](https://github.com/langchain-ai/deepagents) (LangChain and LangGraph-based agent orchestration)
- Daytona sandbox for code execution

## Installation

```bash
uv sync

# Copy environment template and configure
cp .env.example .env
# Substitute .env with your API keys
```

## Usage

```bash
open-mre path/to/issue.md
```

This:

1. Extracts code from the bug report
   1. Validate package versions, if specified (if an issue is opened against legacy versions, the problem may have been fixed in later releases)
2. Execute the code, hydrating with any missing imports or environment setup/entrypoint
3. Report back findings

The CLI shows real-time progress updates as each node executes and is viewable in LangSmith.

### Passing Environment Variables to Sandbox

If the code being tested requires API keys or other environment variables, you can pass them from your host environment to the Daytona sandbox for use when executing the MRE:

```bash
# Pass one or more environment variables
open-mre issue.md -e OPENAI_API_KEY ANTHROPIC_API_KEY DATABASE_URL
```

## Output

Generated files are saved to `outputs/`:

- `outputs/validation_report.md`: Validation results with status (`✅ GREEN`/`🟡 YELLOW`/`❌ RED`)
- `outputs/reproduction.py`: Runnable reproduction script (if successful) for maintainers

Metadata and intermediate files:

- `outputs/execution_results.json`: Raw execution output and metadata
- `outputs/extracted_code.py`: Code extracted from the bug report
- `outputs/version_report.json`: Package version validation results
- `outputs/behavior_analysis.json`: Expected vs actual behavior analysis

## Architecture

The system uses a coordinator agent that delegates to five specialized subagents:

1. **Code Extractor**: Extracts Python code from markdown
2. **Version Validator**: Checks package versions against PyPI
3. **Behavior Analyst**: Parses expected vs actual behavior
4. **Executor**: Runs code in isolated environment
5. **Report Generator**: Creates final validation reports

See `IMPLEMENTATION_SPEC.md` for detailed technical specifications.

## Acknowledgements

@bracesproul for inspiring the [name](https://github.com/langchain-ai/open-swe)

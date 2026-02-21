# `open-mre`

A LangGraph-powered tool to validate Minimal Reproducible Examples (MREs) from inbound GitHub issues.

## Installation

```bash
git clone https://github.com/your-org/open-mre.git
cd open-mre

uv sync
```

## Configuration

Set the required environment variables:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export DAYTONA_API_KEY="your-daytona-api-key"
```

## Usage

```bash
open-mre path/to/issue.md
```

### CLI Options

```txt
open-mre <issue_file> [options]

Arguments:
  issue_file              Path to the GitHub issue markdown file

Options:
  -o, --output-dir DIR    Directory for output files (default: current directory)
  --no-execute            Skip code execution (analysis only)
  --auto-approve-keys     Automatically approve API key usage (use with caution)
```

### Example

```bash
# Basic usage
open-mre ./issues/bug-report-123.md

# Save outputs to a specific directory
open-mre ./issues/bug-report-123.md -o ./reports/

# Analysis only (no sandbox execution)
open-mre ./issues/bug-report-123.md --no-execute
```

## LangGraph Local Server

Run the MRE validator as a LangGraph local server for development and testing:

```bash
uv sync --group dev
uv run langgraph dev
```

This starts an in-memory development server at `http://localhost:2024` with:

- API endpoint: `http://localhost:2024`
- API docs: `http://localhost:2024/docs`
- LangGraph Studio UI via LangSmith

See `IMPLEMENTATION_SPEC.md` for detailed technical specifications.

## Acknowledgements

@bracesproul for inspiring the [name](https://github.com/langchain-ai/open-swe)

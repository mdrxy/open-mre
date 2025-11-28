# `open-mre`

App validating Minimal Reproducible Examples (MREs) from incoming GitHub issues.

## Usage

```bash
open-mre path/to/issue.md
```

This will:

1. Extract code snippets from the bug report
2. Execute the code in a sandboxed container. If needed, the agent will hydrate the snippet(s) with any missing imports or environment setup/entrypoint
3. Report findings by comparing the actual behavior/output against the expected behavior described in the issue

See `IMPLEMENTATION_SPEC.md` for detailed technical specifications.

## Acknowledgements

@bracesproul for inspiring the [name](https://github.com/langchain-ai/open-swe)

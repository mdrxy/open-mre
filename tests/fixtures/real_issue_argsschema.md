### Checked other resources

- [x] This is a bug, not a usage question.
- [x] I added a clear and descriptive title that summarizes this issue.
- [x] I used the GitHub search to find a similar question and didn't find it.
- [x] I am sure that this is a bug in LangChain rather than my code.
- [x] The bug is not resolved by updating to the latest stable version of LangChain (or the specific integration package).
- [x] This is not related to the langchain-community package.
- [x] I read what a minimal reproducible example is (<https://stackoverflow.com/help/minimal-reproducible-example>).
- [x] I posted a self-contained, minimal, reproducible example. A maintainer can copy it and run it AS IS.

### Example Code

Failed code:

```python
from pydantic import BaseModel
from langchain.tools import tool, ToolRuntime


class InputModel(BaseModel):
    query: str


@tool(args_schema=InputModel)
def demo_tool(query: str, runtime: ToolRuntime):
    """Demo tool that just echoes the query."""
    return f"{query=} {runtime=}"


if __name__ == "__main__":
    from langchain.tools.tool_node import ToolRuntime as TR

    runtime = TR(
        state={},
        context=None,
        config={},
        tool_call_id="1",
        store=None,
        stream_writer=None,
    )
    print(demo_tool.invoke({"query": "hello", "runtime": runtime}))
```

Success:

```python
from langchain.tools import tool, ToolRuntime
from pydantic import Field
from typing import Annotated


@tool
def demo_tool(
    query: Annotated[str, Field(description="The query to process")],
    runtime: ToolRuntime,
):
    """Demo tool that just echoes the query."""
    return f"{query=} {runtime=}"


if __name__ == "__main__":
    from langchain.tools.tool_node import ToolRuntime as TR

    runtime = TR(
        state={},
        context=None,
        config={},
        tool_call_id="1",
        store=None,
        stream_writer=None,
    )
    print(demo_tool.invoke({"query": "hello", "runtime": runtime}))
```

### Error Message and Stack Trace (if applicable)

Traceback (most recent call last):
  File "/Users/leopham/Documents/sapia/tia/fail.py", line 26, in <module>
    print(demo_tool.invoke({"query": "hello", "runtime": runtime}))
          ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/leopham/Documents/sapia/tia/.venv/lib/python3.13/site-packages/langchain_core/tools/base.py", line 591, in invoke
    return self.run(tool_input, **kwargs)
           ~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/leopham/Documents/sapia/tia/.venv/lib/python3.13/site-packages/langchain_core/tools/base.py", line 856, in run
    raise error_to_raise
  File "/Users/leopham/Documents/sapia/tia/.venv/lib/python3.13/site-packages/langchain_core/tools/base.py", line 825, in run
    response = context.run(self._run, *tool_args,**tool_kwargs)
  File "/Users/leopham/Documents/sapia/tia/.venv/lib/python3.13/site-packages/langchain_core/tools/structured.py", line 90, in_run
    return self.func(*args, **kwargs)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^
TypeError: demo_tool() missing 1 required positional argument: 'runtime'

### Description

I am trying to set up the args_schema to tool function with Pydantic BaseModel

### System Info

sys_info.print_sys_info()

633;Bsys_info.print_sys_info()

System Information
------------------
>
> OS:  Darwin
> OS Version:  Darwin Kernel Version 24.6.0: Mon Aug 11 21:16:34 PDT 2025; root:xnu-11417.140.69.701.11~1/RELEASE_ARM64_T6020
> Python Version:  3.13.1 (main, Dec  3 2024, 17:59:52) [Clang 16.0.0 (clang-1600.0.26.4)]

Package Information
-------------------
>
> langchain_core: 1.0.0
> langchain: 1.0.0
> langchain_community: 1.0.0a1
> langsmith: 0.4.37
> langchain_aws: 1.0.0
> langchain_classic: 1.0.0
> langchain_text_splitters: 1.0.0
> langgraph_sdk: 0.2.9

Optional packages not installed
-------------------------------
>
> langserve

Other Dependencies
------------------
>
> aiohttp: 3.13.1
> async-timeout: Installed. No version info available.
> beautifulsoup4: Installed. No version info available.
> bedrock-agentcore: Installed. No version info available.
> boto3: 1.40.19
> claude-agent-sdk: Installed. No version info available.
> dataclasses-json: 0.6.7
> httpx: 0.27.0
> httpx-sse: 0.4.3
> jsonpatch: 1.33
> langchain-anthropic: Installed. No version info available.
> langchain-deepseek: Installed. No version info available.
> langchain-fireworks: Installed. No version info available.
> langchain-google-genai: Installed. No version info available.
> langchain-google-vertexai: Installed. No version info available.
> langchain-groq: Installed. No version info available.
> langchain-huggingface: Installed. No version info available.
> langchain-mistralai: Installed. No version info available.
> langchain-ollama: Installed. No version info available.
> langchain-openai: Installed. No version info available.
> langchain-perplexity: Installed. No version info available.
> langchain-together: Installed. No version info available.
> langchain-xai: Installed. No version info available.
> langgraph: 1.0.0
> langsmith-pyo3: Installed. No version info available.
> numpy: 2.3.4
> openai-agents: Installed. No version info available.
> opentelemetry-api: 1.38.0
> opentelemetry-exporter-otlp-proto-http: 1.38.0
> opentelemetry-sdk: 1.38.0
> orjson: 3.11.3
> packaging: 25.0
> playwright: Installed. No version info available.
> pydantic: 2.10.6
> pydantic-settings: 2.10.1
> pytest: 8.4.2
> pyyaml: 6.0.3
> PyYAML: 6.0.3
> requests: 2.32.5
> requests-toolbelt: 1.0.0
> rich: Installed. No version info available.
> sqlalchemy: 2.0.44
> SQLAlchemy: 2.0.44
> tenacity: 9.1.2
> typing-extensions: 4.15.0
> vcrpy: Installed. No version info available.
> zstandard: 0.25.0

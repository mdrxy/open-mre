### Checked other resources

- [x] This is a bug, not a usage question. For questions, please use the LangChain Forum (<https://forum.langchain.com/>).
- [x] I added a clear and descriptive title that summarizes this issue.
- [x] I used the GitHub search to find a similar question and didn't find it.
- [x] I am sure that this is a bug in LangChain rather than my code.
- [x] The bug is not resolved by updating to the latest stable version of LangChain (or the specific integration package).
- [x] I read what a minimal reproducible example is (<https://stackoverflow.com/help/minimal-reproducible-example>).
- [x] I posted a self-contained, minimal, reproducible example. A maintainer can copy it and run it AS IS.

### Example Code

It is impossible to reproduce the bug with just a code example.

### Error Message and Stack Trace (if applicable)

_No response_

### Description

Changes from [PR](https://github.com/langchain-ai/langchain/pull/31587) added a function [_advance](https://github.com/langchain-ai/langchain/blob/4656f727da238c1fe24f95698842b94d579844c2/libs/partners/openai/langchain_openai/chat_models/base.py#L3995) to chunk processing that changes the index variable. This creates a bug that corrupts arguments for custom functions that are called after a document search.

The sequence of events to reproduce the bug:

1. Start a chat with the Responses API and the document search function
2. The model uses document search
3. The model calls the custom function and starts passing arguments:
`{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": " battery", "item_id": "..., "output_index": 1, "sequence_number": 165, "type": "response.function_call_arguments.delta", "obfuscation": "..."}
{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": " supply", "item_id": "....", "output_index": 1, "sequence_number": 166, "type": "response.function_call_arguments.delta", "obfuscation": "..."}
{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": " chain", "item_id": "....", "output_index": 1, "sequence_number": 167, "type": "response.function_call_arguments.delta", "obfuscation": "..."}`
4. At this point, the chunk index is 1
`{"name": null, "args": "-loop", "id": null, "index": 1, "type": "tool_call_chunk"}
{"name": null, "args": " supply", "id": null, "index": 1, "type": "tool_call_chunk"}
{"name": null, "args": " chain", "id": null, "index": 1, "type": "tool_call_chunk"}`
5. The model adds an annotation:
`{"type": "response.output_text.annotation.added", "output_index": 1, "raw": {"annotation": {"type": "file_citation", "file_id": "...", "filename": "...", "index": 794}, "annotation_index": 0, "content_index": 0, "item_id": "...", "output_index": 1, "sequence_number": 168, "type": "response.output_text.annotation.added"}}`
6. For annotations, the function with the parameter sub_idx ```_advance(chunk.output_index, chunk.content_index)``` is used, and for tool arguments without the parameter sub_idx ```_advance(chunk.output_index)```
7. Because the ```sub_idx``` parameter was not previously passed, ```current_sub_index = -1```, and the new ```sub_idx = 0```. This results in 1 being added to ```current_index```.
8. The model continues to pass arguments:
`{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": ".\\", "item_id": "...", "output_index": 1, "sequence_number": 169, "type": "response.function_call_arguments.delta", "obfuscation": "..."}}
{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": "n", "item_id": "...", "output_index": 1, "sequence_number": 170, "type": "response.function_call_arguments.delta", "obfuscation": "..."}}
{"type": "response.function_call_arguments.delta", "output_index": 1, "raw": {"delta": "\\n", "item_id": "...", "output_index": 1, "sequence_number": 171, "type": "response.function_call_arguments.delta", "obfuscation": "..."}}`
9. Now when current_index = 2, chunk index is also 2:
`{"name": null, "args": ".\\", "id": null, "index": 2, "type": "tool_call_chunk"}
{"name": null, "args": "n", "id": null, "index": 2, "type": "tool_call_chunk"}
{"name": null, "args": "\\n", "id": null, "index": 2, "type": "tool_call_chunk"}`
10. After streaming the chunks, due to the fact that chunks have different indices, we have the beginning of the tool call and part of the argument written in ```tool_calls```. We also have the rest of the arguments written in ```invalid_tool_calls```:
`{"tool_calls": [
              {
                "name": "custom_tool",
                "args": {
                  "final_result": "... supply chain"
                },
                "id": "...",
                "type": "tool_call"
              }
            ],
  "invalid_tool_calls": [
              {
                "name": null,
                "args": ".\\n\\n2. .... \",\"article_attribution\":[]}",
                "id": null,
                "error": null,
                "type": "invalid_tool_call"
              }
            ]}`

@ccurme Could you take a look at this?

### System Info

System Information
------------------
>
> OS:  Linux
> OS Version:  #1 SMP Sat Jun  7 02:45:18 UTC 2025
> Python Version:  3.10.10 (main, Mar 23 2023, 03:59:01) [GCC 10.2.1 20210110]

Package Information
-------------------
>
> langchain_core: 0.3.74
> langchain: 0.3.27
> langchain_community: 0.3.27
> langsmith: 0.4.14
> langchain_openai: 0.3.30
> langchain_pinecone: 0.2.6
> langchain_tests: 0.3.20
> langchain_text_splitters: 0.3.9
> langgraph_sdk: 0.2.0

Optional packages not installed
-------------------------------
>
> langserve

Other Dependencies
------------------
>
> aiohttp<3.11,>=3.10: Installed. No version info available.
> aiohttp<4.0.0,>=3.8.3: Installed. No version info available.
> async-timeout<5.0.0,>=4.0.0;: Installed. No version info available.
> dataclasses-json<0.7,>=0.5.7: Installed. No version info available.
> httpx-sse<1.0.0,>=0.4.0: Installed. No version info available.
> httpx<1,>=0.23.0: Installed. No version info available.
> httpx<1,>=0.25.0: Installed. No version info available.
> httpx>=0.25.2: Installed. No version info available.
> jsonpatch<2.0,>=1.33: Installed. No version info available.
> langchain-anthropic;: Installed. No version info available.
> langchain-aws;: Installed. No version info available.
> langchain-azure-ai;: Installed. No version info available.
> langchain-cohere;: Installed. No version info available.
> langchain-community;: Installed. No version info available.
> langchain-core<1.0.0,>=0.3.34: Installed. No version info available.
> langchain-core<1.0.0,>=0.3.63: Installed. No version info available.
> langchain-core<1.0.0,>=0.3.66: Installed. No version info available.
> langchain-core<1.0.0,>=0.3.72: Installed. No version info available.
> langchain-core<1.0.0,>=0.3.74: Installed. No version info available.
> langchain-deepseek;: Installed. No version info available.
> langchain-fireworks;: Installed. No version info available.
> langchain-google-genai;: Installed. No version info available.
> langchain-google-vertexai;: Installed. No version info available.
> langchain-groq;: Installed. No version info available.
> langchain-huggingface;: Installed. No version info available.
> langchain-mistralai;: Installed. No version info available.
> langchain-ollama;: Installed. No version info available.
> langchain-openai;: Installed. No version info available.
> langchain-perplexity;: Installed. No version info available.
> langchain-tests<1.0.0,>=0.3.7: Installed. No version info available.
> langchain-text-splitters<1.0.0,>=0.3.9: Installed. No version info available.
> langchain-together;: Installed. No version info available.
> langchain-xai;: Installed. No version info available.
> langchain<1.0.0,>=0.3.26: Installed. No version info available.
> langsmith-pyo3>=0.1.0rc2;: Installed. No version info available.
> langsmith>=0.1.125: Installed. No version info available.
> langsmith>=0.1.17: Installed. No version info available.
> langsmith>=0.3.45: Installed. No version info available.
> numpy>=1.26.2;: Installed. No version info available.
> numpy>=1.26.4: Installed. No version info available.
> numpy>=2.1.0;: Installed. No version info available.
> openai-agents>=0.0.3;: Installed. No version info available.
> openai<2.0.0,>=1.99.9: Installed. No version info available.
> opentelemetry-api>=1.30.0;: Installed. No version info available.
> opentelemetry-exporter-otlp-proto-http>=1.30.0;: Installed. No version info available.
> opentelemetry-sdk>=1.30.0;: Installed. No version info available.
> orjson>=3.10.1: Installed. No version info available.
> orjson>=3.9.14;: Installed. No version info available.
> packaging>=23.2: Installed. No version info available.
> pinecone[async]<7.0.0,>=6.0.0: Installed. No version info available.
> pydantic-settings<3.0.0,>=2.4.0: Installed. No version info available.
> pydantic<3,>=1: Installed. No version info available.
> pydantic<3.0.0,>=2.7.4: Installed. No version info available.
> pydantic>=2.7.4: Installed. No version info available.
> pytest-asyncio<1,>=0.20: Installed. No version info available.
> pytest-benchmark: 5.0.1
> pytest-codspeed: 4.0.0
> pytest-recording: 0.13.4
> pytest-socket<1,>=0.6.0: Installed. No version info available.
> pytest<9,>=7: Installed. No version info available.
> pytest>=7.0.0;: Installed. No version info available.
> PyYAML>=5.3: Installed. No version info available.
> requests-toolbelt>=1.0.0: Installed. No version info available.
> requests<3,>=2: Installed. No version info available.
> requests>=2.0.0: Installed. No version info available.
> rich>=13.9.4;: Installed. No version info available.
> SQLAlchemy<3,>=1.4: Installed. No version info available.
> syrupy<5,>=4: Installed. No version info available.
> tenacity!=8.4.0,<10,>=8.1.0: Installed. No version info available.
> tenacity!=8.4.0,<10.0.0,>=8.1.0: Installed. No version info available.
> tiktoken<1,>=0.7: Installed. No version info available.
> typing-extensions>=4.7: Installed. No version info available.
> vcrpy>=7.0: Installed. No version info available.
> vcrpy>=7.0.0;: Installed. No version info available.
> zstandard>=0.23.0: Installed. No version info available.

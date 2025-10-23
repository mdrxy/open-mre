### Checked other resources

- [x] This is a bug, not a usage question. For questions, please use the LangChain Forum (<https://forum.langchain.com/>).
- [x] I added a clear and descriptive title that summarizes this issue.
- [x] I used the GitHub search to find a similar question and didn't find it.
- [x] I am sure that this is a bug in LangChain rather than my code.
- [x] The bug is not resolved by updating to the latest stable version of LangChain (or the specific integration package).
- [x] I read what a minimal reproducible example is (<https://stackoverflow.com/help/minimal-reproducible-example>).
- [x] I posted a self-contained, minimal, reproducible example. A maintainer can copy it and run it AS IS.

### Example Code

## Error code

```python
from langchain_openai import AzureChatOpenAI

model = AzureChatOpenAI(
    api_key='apikey',
    azure_endpoint='https://xxxxxxxx.openai.azure.com/',
    azure_deployment='gpt-5-nano',
    api_version= '2025-03-01-preview',
    model_kwargs={"text": {"verbosity": "high"}},
    reasoning={
        "effort": "medium",
        "summary": "detailed" # auto, concise, or detailed, gpt-5 series do not support concise 
    }, 
)

model.invoke('2+2/4')
```

## Got error

```
---------------------------------------------------------------------------
NotFoundError                             Traceback (most recent call last)
Cell In[33], line 1
----> 1 model.invoke('2+2/4')

File virtualenvs\GenAI\Lib\site-packages\langchain_core\language_models\chat_models.py:393, in BaseChatModel.invoke(self, input, config, stop, **kwargs)
    381 @override
    382 def invoke(
    383     self,
   (...)    388     **kwargs: Any,
    389 ) -> BaseMessage:
    390     config = ensure_config(config)
    391     return cast(
    392         "ChatGeneration",
--> 393         self.generate_prompt(
    394             [self._convert_input(input)],
    395             stop=stop,
    396             callbacks=config.get("callbacks"),
    397             tags=config.get("tags"),
    398             metadata=config.get("metadata"),
    399             run_name=config.get("run_name"),
    400             run_id=config.pop("run_id", None),
    401             **kwargs,
    402         ).generations[0][0],
    403     ).message

File dvirtualenvs\GenAI\Lib\site-packages\langchain_core\language_models\chat_models.py:1019, in BaseChatModel.generate_prompt(self, prompts, stop, callbacks, **kwargs)
   1010 @override
   1011 def generate_prompt(
   1012     self,
   (...)   1016     **kwargs: Any,
   1017 ) -> LLMResult:
   1018     prompt_messages = [p.to_messages() for p in prompts]
-> 1019     return self.generate(prompt_messages, stop=stop, callbacks=callbacks, **kwargs)

File virtualenvs\GenAI\Lib\site-packages\langchain_core\language_models\chat_models.py:837, in BaseChatModel.generate(self, messages, stop, callbacks, tags, metadata, run_name, run_id, **kwargs)
    834 for i, m in enumerate(input_messages):
    835     try:
    836         results.append(
--> 837             self._generate_with_cache(
    838                 m,
    839                 stop=stop,
    840                 run_manager=run_managers[i] if run_managers else None,
    841                 **kwargs,
    842             )
    843         )
    844     except BaseException as e:
    845         if run_managers:

File virtualenvs\GenAI\Lib\site-packages\langchain_core\language_models\chat_models.py:1085, in BaseChatModel._generate_with_cache(self, messages, stop, run_manager, **kwargs)
   1083     result = generate_from_stream(iter(chunks))
   1084 elif inspect.signature(self._generate).parameters.get("run_manager"):
-> 1085     result = self._generate(
   1086         messages, stop=stop, run_manager=run_manager, **kwargs
   1087     )
   1088 else:
   1089     result = self._generate(messages, stop=stop, **kwargs)

File virtualenvs\GenAI\Lib\site-packages\langchain_openai\chat_models\base.py:1062, in BaseChatOpenAI._generate(self, messages, stop, run_manager, **kwargs)
   1060             generation_info = {"headers": dict(raw_response.headers)}
   1061         else:
-> 1062             response = self.root_client.responses.create(**payload)
   1063     return _construct_lc_result_from_responses_api(
   1064         response, schema=original_schema_obj, metadata=generation_info
   1065     )
   1066 elif self.include_response_headers:

File virtualenvs\GenAI\Lib\site-packages\openai\resources\responses\responses.py:814, in Responses.create(self, background, conversation, include, input, instructions, max_output_tokens, max_tool_calls, metadata, model, parallel_tool_calls, previous_response_id, prompt, prompt_cache_key, reasoning, safety_identifier, service_tier, store, stream, stream_options, temperature, text, tool_choice, tools, top_logprobs, top_p, truncation, user, extra_headers, extra_query, extra_body, timeout)
    777 def create(
    778     self,
    779     *,
   (...)    812     timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    813 ) -> Response | Stream[ResponseStreamEvent]:
--> 814     return self._post(
    815         "/responses",
    816         body=maybe_transform(
    817             {
    818                 "background": background,
    819                 "conversation": conversation,
    820                 "include": include,
    821                 "input": input,
    822                 "instructions": instructions,
    823                 "max_output_tokens": max_output_tokens,
    824                 "max_tool_calls": max_tool_calls,
    825                 "metadata": metadata,
    826                 "model": model,
    827                 "parallel_tool_calls": parallel_tool_calls,
    828                 "previous_response_id": previous_response_id,
    829                 "prompt": prompt,
    830                 "prompt_cache_key": prompt_cache_key,
    831                 "reasoning": reasoning,
    832                 "safety_identifier": safety_identifier,
    833                 "service_tier": service_tier,
    834                 "store": store,
    835                 "stream": stream,
    836                 "stream_options": stream_options,
    837                 "temperature": temperature,
    838                 "text": text,
    839                 "tool_choice": tool_choice,
    840                 "tools": tools,
    841                 "top_logprobs": top_logprobs,
    842                 "top_p": top_p,
    843                 "truncation": truncation,
    844                 "user": user,
    845             },
    846             response_create_params.ResponseCreateParamsStreaming
    847             if stream
    848             else response_create_params.ResponseCreateParamsNonStreaming,
    849         ),
    850         options=make_request_options(
    851             extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
    852         ),
    853         cast_to=Response,
    854         stream=stream or False,
    855         stream_cls=Stream[ResponseStreamEvent],
    856     )

File virtualenvs\GenAI\Lib\site-packages\openai\_base_client.py:1259, in SyncAPIClient.post(self, path, cast_to, body, options, files, stream, stream_cls)
   1245 def post(
   1246     self,
   1247     path: str,
   (...)   1254     stream_cls: type[_StreamT] | None = None,
   1255 ) -> ResponseT | _StreamT:
   1256     opts = FinalRequestOptions.construct(
   1257         method="post", url=path, json_data=body, files=to_httpx_files(files), **options
   1258     )
-> 1259     return cast(ResponseT, self.request(cast_to, opts, stream=stream, stream_cls=stream_cls))

File virtualenvs\GenAI\Lib\site-packages\openai\_base_client.py:1047, in SyncAPIClient.request(self, cast_to, options, stream, stream_cls)
   1044             err.response.read()
   1046         log.debug("Re-raising status error")
-> 1047         raise self._make_status_error_from_response(err.response) from None
   1049     break
   1051 assert response is not None, "could not resolve response (should never happen)"

NotFoundError: Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}
```

### Please note that if I remove

```
reasoning={
        "effort": "medium",
        "summary": "detailed" # auto, concise, or detailed, gpt-5 series do not support concise 
    }
```

the code works fine i.e. the `NotFoundError` is not correct in this case

## Working code with native AzureOpenai

```python
from openai import AzureOpenAI


client = AzureOpenAI(  
    api_key='apikey',
    azure_endpoint='https://xxxxxx.openai.azure.com/',
    api_version="2025-03-01-preview"
)

response = client.responses.create(
    input="2+2/10",
    model="gpt-5-nano", # replace with model deployment name
    reasoning={
        "effort": "medium",
        "summary": "auto" # auto, concise, or detailed, gpt-5 series do not support concise 
    },
    text={
        "verbosity": "high" # New with GPT-5 models
    },
    stream=True
)

for chunk in response:
    print(chunk)
```

## Output: with streaming reasoning

```
ResponseCreatedEvent(response=Response(id='resp_68af15aadb208190acbeee7acf3855880f1ea50ddfb9ad5c', created_at=1756304811.0, error=None, incomplete_details=None, instructions=None, metadata={}, model='gpt-5-nano', object='response', output=[], parallel_tool_calls=True, temperature=1.0, tool_choice='auto', tools=[], top_p=1.0, background=False, conversation=None, max_output_tokens=None, max_tool_calls=None, previous_response_id=None, prompt=None, prompt_cache_key=None, reasoning=Reasoning(effort='medium', generate_summary=None, summary='detailed'), safety_identifier=None, service_tier='auto', status='in_progress', text=ResponseTextConfig(format=ResponseFormatText(type='text'), verbosity=None), top_logprobs=None, truncation='disabled', usage=None, user=None, content_filters=None, store=True), sequence_number=0, type='response.created')
ResponseInProgressEvent(response=Response(id='resp_68af15aadb208190acbeee7acf3855880f1ea50ddfb9ad5c', created_at=1756304811.0, error=None, incomplete_details=None, instructions=None, metadata={}, model='gpt-5-nano', object='response', output=[], parallel_tool_calls=True, temperature=1.0, tool_choice='auto', tools=[], top_p=1.0, background=False, conversation=None, max_output_tokens=None, max_tool_calls=None, previous_response_id=None, prompt=None, prompt_cache_key=None, reasoning=Reasoning(effort='medium', generate_summary=None, summary='detailed'), safety_identifier=None, service_tier='auto', status='in_progress', text=ResponseTextConfig(format=ResponseFormatText(type='text'), verbosity=None), top_logprobs=None, truncation='disabled', usage=None, user=None, content_filters=None, store=True), sequence_number=1, type='response.in_progress')
ResponseOutputItemAddedEvent(item=ResponseReasoningItem(id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', summary=[], type='reasoning', content=None, encrypted_content=None, status=None), output_index=0, sequence_number=2, type='response.output_item.added')
ResponseReasoningSummaryPartAddedEvent(item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, part=Part(text='', type='summary_text'), sequence_number=3, summary_index=0, type='response.reasoning_summary_part.added')
ResponseReasoningSummaryTextDeltaEvent(delta='**Calcul', item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, sequence_number=4, summary_index=0, type='response.reasoning_summary_text.delta')
ResponseReasoningSummaryTextDeltaEvent(delta='ating', item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, sequence_number=5, summary_index=0, type='response.reasoning_summary_text.delta')
ResponseReasoningSummaryTextDeltaEvent(delta=' user', item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, sequence_number=6, summary_index=0, type='response.reasoning_summary_text.delta')
ResponseReasoningSummaryTextDeltaEvent(delta='!', item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, sequence_number=221, summary_index=1, type='response.reasoning_summary_text.delta')
ResponseReasoningSummaryTextDoneEvent(item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, sequence_number=222, summary_index=1, text='**Presenting math solution**\n\nI want to ensure I provide a clear answer to the user's math problem. I\'ll show the calculation as: "2 + 2/10 = 2 + 1/5 = 11/5 = 2.2." It\'s worth mentioning that 2/10 simplifies down to 1/5. I also wonder if the user prefers a decimal or a fraction, so I'll present both formats. It's all about clarity and making sure the user gets the information they need in a straightforward manner!', type='response.reasoning_summary_text.done')
ResponseReasoningSummaryPartDoneEvent(item_id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', output_index=0, part=Part(text='**Presenting math solution**\n\nI want to ensure I provide a clear answer to the user's math problem. I\'ll show the calculation as: "2 + 2/10 = 2 + 1/5 = 11/5 = 2.2." It\'s worth mentioning that 2/10 simplifies down to 1/5. I also wonder if the user prefers a decimal or a fraction, so I'll present both formats. It's all about clarity and making sure the user gets the information they need in a straightforward manner!', type='summary_text'), sequence_number=223, summary_index=1, type='response.reasoning_summary_part.done')
ResponseOutputItemDoneEvent(item=ResponseReasoningItem(id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', summary=[Summary(text='**Calculating user math request**\n\nThe user asked for "2 + 2/10." To solve this, I\'ll follow the order of operations: division before addition. That means 2 + 2/10 equals 2 + 0.2, which simplifies to 2.2. I can also present this result as a fraction: 11/5. It would be helpful to show the steps, too: 2/10 reduces to 1/5, then 2 + 1/5 equals 11/5. So my answer will be 2.2 or 11/5 with a brief explanation.', type='summary_text'), Summary(text='**Presenting math solution**\n\nI want to ensure I provide a clear answer to the user's math problem. I\'ll show the calculation as: "2 + 2/10 = 2 + 1/5 = 11/5 = 2.2." It\'s worth mentioning that 2/10 simplifies down to 1/5. I also wonder if the user prefers a decimal or a fraction, so I'll present both formats. It's all about clarity and making sure the user gets the information they need in a straightforward manner!', type='summary_text')], type='reasoning', content=None, encrypted_content=None, status=None), output_index=0, sequence_number=224, type='response.output_item.done')
ResponseContentPartDoneEvent(content_index=0, item_id='msg_68af15af8f608190bb3d1e9725dd30e40f1ea50ddfb9ad5c', output_index=1, part=ResponseOutputText(annotations=[], text='2 + 2/10 = 2 + 1/5 = 11/5 = 2.2\n\nSo the result is 2.2 (or 11/5 in fraction form).', type='output_text', logprobs=None), sequence_number=271, type='response.content_part.done')
ResponseOutputItemDoneEvent(item=ResponseOutputMessage(id='msg_68af15af8f608190bb3d1e9725dd30e40f1ea50ddfb9ad5c', content=[ResponseOutputText(annotations=[], text='2 + 2/10 = 2 + 1/5 = 11/5 = 2.2\n\nSo the result is 2.2 (or 11/5 in fraction form).', type='output_text', logprobs=None)], role='assistant', status='completed', type='message'), output_index=1, sequence_number=272, type='response.output_item.done')
ResponseCompletedEvent(response=Response(id='resp_68af15aadb208190acbeee7acf3855880f1ea50ddfb9ad5c', created_at=1756304811.0, error=None, incomplete_details=None, instructions=None, metadata={}, model='gpt-5-nano', object='response', output=[ResponseReasoningItem(id='rs_68af15abcfe881909e34dd1b47dfa9170f1ea50ddfb9ad5c', summary=[Summary(text='**Calculating user math request**\n\nThe user asked for "2 + 2/10." To solve this, I\'ll follow the order of operations: division before addition. That means 2 + 2/10 equals 2 + 0.2, which simplifies to 2.2. I can also present this result as a fraction: 11/5. It would be helpful to show the steps, too: 2/10 reduces to 1/5, then 2 + 1/5 equals 11/5. So my answer will be 2.2 or 11/5 with a brief explanation.', type='summary_text'), Summary(text='**Presenting math solution**\n\nI want to ensure I provide a clear answer to the user's math problem. I\'ll show the calculation as: "2 + 2/10 = 2 + 1/5 = 11/5 = 2.2." It\'s worth mentioning that 2/10 simplifies down to 1/5. I also wonder if the user prefers a decimal or a fraction, so I'll present both formats. It's all about clarity and making sure the user gets the information they need in a straightforward manner!', type='summary_text')], type='reasoning', content=None, encrypted_content=None, status=None), ResponseOutputMessage(id='msg_68af15af8f608190bb3d1e9725dd30e40f1ea50ddfb9ad5c', content=[ResponseOutputText(annotations=[], text='2 + 2/10 = 2 + 1/5 = 11/5 = 2.2\n\nSo the result is 2.2 (or 11/5 in fraction form).', type='output_text', logprobs=None)], role='assistant', status='completed', type='message')], parallel_tool_calls=True, temperature=1.0, tool_choice='auto', tools=[], top_p=1.0, background=False, conversation=None, max_output_tokens=None, max_tool_calls=None, previous_response_id=None, prompt=None, prompt_cache_key=None, reasoning=Reasoning(effort='medium', generate_summary=None, summary='detailed'), safety_identifier=None, service_tier='default', status='completed', text=ResponseTextConfig(format=ResponseFormatText(type='text'), verbosity=None), top_logprobs=None, truncation='disabled', usage=ResponseUsage(input_tokens=11, input_tokens_details=InputTokensDetails(cached_tokens=0), output_tokens=369, output_tokens_details=OutputTokensDetails(reasoning_tokens=320), total_tokens=380), user=None, content_filters=None, store=True), sequence_number=273, type='response.completed')
```

### Error Message and Stack Trace (if applicable)

_No response_

### Description

I'm trying to stream the AzureOpenAi GPT-5 Nano reasoning step on the user interface using `AzureChatOpenAI`. I'm not able to get the reasoning summary in the streaming response. Also, passing `reasoning` in `AzureChatOpenAI` gives `NotFoundError: Error code: 404 - {'error': {'code': 'DeploymentNotFound', 'message': 'The API deployment for this resource does not exist. If you created the deployment within the last 5 minutes, please wait a moment and try again.'}}` error. This error is wrong as the resource is there, and it works fine if I remove the `reasoning` parameter from `AzureChatOpenAI`.

### System Info

System Information
------------------
>
> OS:  Windows
> OS Version:  10.0.26100
> Python Version:  3.12.11 (main, Jun 12 2025, 12:44:17) [MSC v.1943 64 bit (AMD64)]

Package Information
-------------------
>
> langchain_core: 0.3.75
> langchain: 0.3.27
> langchain_community: 0.3.27
> langsmith: 0.4.19
> langchain_anthropic: 0.3.19
> langchain_chroma: 0.2.4
> langchain_docling: 1.0.0
> langchain_experimental: 0.3.4
> langchain_huggingface: 0.3.0
> langchain_ollama: 0.3.6
> langchain_openai: 0.3.25
> langchain_pymupdf4llm: 0.4.1
> langchain_qdrant: 0.2.0
> langchain_tavily: 0.2.11
> langchain_text_splitters: 0.3.9
> langchain_unstructured: 0.1.6
> langgraph_sdk: 0.2.3
> langgraph_supervisor: 0.0.29

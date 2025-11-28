# System architecture

## High-level flow

Input: issue.md (raw body content from a newly submitted GitHub issue)

Steps:

The following steps are only performed on GitHub's NEW_ISSUE event. This means that the workflow is triggered only when a new issue is created, not on edits or comments; there will only be the issue body content available as input.

1. Enrichment:
   1. Version validation: it is useful for maintainers to know which package versions and Python version the user is using when reporting an issue. This step ensures that the package versions are clearly identified and validated.
      1. Python version: extract the Python version from the issue content. If the user does not specify a Python version: make a note that they didn't specify it and proceed.
      2. Dependency versions: identify the main package(s) mentioned in the issue (e.g., `langchain`, `langchain-openai`, etc.) and extract their versions if specified.
         1. If the user specifies package version(s): validate that they using the latest release(s) available on PyPI for each package. If **any** package is outdated, we make a note of this and terminate early.
         2. If the user does not specify package version(s), we make a note of this, assuming they are on the latest.
      3. Review notes before proceeding: compile the findings from the version validations to determine whether we can proceed.
         1. If the user indicated use of an outdated dependency, we cannot proceed. Using all other notes (e.g. not specifying Python version or package versions), draft a response for a comment on the issue stating that maintainers will not address the issue until the user upgrades to the latest package version(s) and confirms that the issue persists. If they also didn't specify the Python version used, include that in the message as well and ask them to provide it. Ask them to edit the issue to include this information.
            1. Draft a response accordingly and comment on the issue along the lines of:
               1. "Hi, I'm an automated bot that helps triage issues. I noticed you are using an outdated version of `langchain` (you indicated version `0.0.150`, while the latest is `0.0.170`). Please upgrade to the latest version and confirm if the issue persists."
               2. "Also, I noticed you did not specify the Python version you are using. It is helpful for maintainers to know this; please edit your issue to include this information."
            2. Enrich the response with the names of the actual packages mentioned in the issue, e.g.:
               1. "Hi, I'm an automated bot that helps triage issues. I noticed you are using an outdated version of `langchain-anthropic` (you indicated version `1.0.0`, while the latest is `1.2.0`). Please upgrade to `1.2.0` and confirm if the issue persists."
            3. The action of actually commenting on the issue will be handled asynchronously outside of this flow. It will include a human-in-the-loop step for maintainers to review and approve the comment before it is posted. We DO NOT proceed further in this application if the user is on outdated versions; the graph should terminate here after submitting the comment HITL step to maintainers.
         2. If the user did not specify either package or Python versions, before moving on to the next step, save notes indicating which information was missing. This information may be used in future steps to draft comments on the issue asking for the missing information.
   2. If we are allowed to continue (e.g. we did not terminate early, save notes from version validation to state so that future steps can reference them as needed.)
2. Code extraction: at this point we either have confirmation that the user is on the latest package versions, or we are assuming so in the absence of version information. Next, we proceed to extract any code snippets from the issue content that may help reproduce the reported behavior. At this step, we parse the issue body to identify code blocks and extract them for further analysis. This will usually involve looking for markdown code fences (triple backticks) and extracting the enclosed code, however, some novice users may not use proper markdown formatting, so we may need to employ some heuristics to identify code snippets that are not properly fenced. In this step, we validate the presence of a MRE.
   1. If no code snippets are found, we draft a response to comment on the issue asking the user to provide a minimal reproducible example (MRE) to help maintainers investigate the issue. The action of commenting on the issue will be handled asynchronously outside of this flow, including a human-in-the-loop step for maintainers to review and approve the comment before it is posted.
      1. Draft a response accordingly and comment on the issue along the lines of:
         1. "Hi, I'm an automated bot that helps triage issues. I noticed you did not provide a minimal reproducible example (MRE) in your issue. To help maintainers investigate the issue, we need a code snippet that reproduces the behavior you are reporting. Please edit your issue to include this information."
      2. When drafting the response, reference any notes from the version validation step about missing package or Python version information, and include requests for that information as well if applicable.
      3. Examples:
         1. "Hi, I'm an automated bot that helps triage issues. I noticed you did not provide a minimal reproducible example (MRE) in your issue. To help maintainers investigate the issue, we need a code snippet that reproduces the behavior you are reporting."
         2. "Also, I noticed you did not specify the version of `langchain-anthropic` that you are using. Please confirm that you are using `1.2.0`, which is the latest released version on PyPI."
         3. "Finally, I noticed you did not specify the Python version you are using. Please provide that information as well."
      4. After drafting the response, the action of commenting on the issue will be handled asynchronously outside of this flow. It will include a human-in-the-loop step for maintainers to review and approve the comment before it is posted. We DO NOT proceed further in this application if no code snippets are found; the graph should terminate here after submitting the comment HITL step to maintainers. We can not reproduce the issue without a MRE.
   2. If code snippets are found, we proceed to the next step, saving the extracted code snippets to state for further analysis in subsequent steps. Remember; at this point we have either confirmed the user is on the latest package versions, or are assuming so in the absence of version information. This information may be useful in future steps.
3. Behavior analysis: with both the extracted code snippets and the issue description available, we analyze the reported behavior to understand what the user is trying to achieve and identify potential points of failure in the provided code. This step may involve parsing the code snippets to identify key functions, classes, or modules being used, as well as cross-referencing with the issue description to understand the context of the reported behavior. The goal is to gain an understanding of the issue at hand to inform the subsequent reproduction and reporting steps. We do not infer any missing information at this point; we simply analyze what is provided. This step prepares us for the next step, where we attempt to reproduce the reported behavior.
   1. If the analysis indicates that critical information is missing that prevents us from understanding the reported behavior (e.g., missing dependencies, unclear context, etc.), we draft a response to comment on the issue asking the user to provide the missing information. The action of commenting on the issue will be handled asynchronously outside of this flow, including a human-in-the-loop step for maintainers to review and approve the comment before it is posted.
      1. Draft a response accordingly and comment on the issue along the lines of:
         1. "Hi, I'm an automated bot that helps triage issues. I noticed that some critical information is missing from your issue that prevents us from fully understanding the reported behavior. Specifically, we need to know what behavior you currently observe, versus what you expect to happen. Please edit your issue to include this information."
            1. If possible, enrich this draft with information on how to find the information they need in the docs. This enirchment will use the LangChain docs to provide specific guidance, matching the context of the issue. For example, if the issue relates to `Agents`, we can point them to the relevant section in the LangChain docs about Agents: "Based on what we can tell from your issue, it seems you are working with Agents. You can find more information about Agents in the LangChain docs here: <https://docs.langchain.com/docs/getting_started/agents/>."
      2. After drafting the response, the action of commenting on the issue will be handled asynchronously outside of this flow. It will include a human-in-the-loop step for maintainers to review and approve the comment before it is posted. We DO NOT proceed further in this application if critical information is missing; the graph should terminate here after submitting the comment HITL step to maintainers.
   2. If the analysis is successful and we have sufficient information to understand the reported behavior, we proceed to the next step, saving any relevant findings to state for use in subsequent steps. Remember: at this point we have both the extracted code snippets and the issue description available for analysis in order to validate our understanding of the reported behavior. Also, we have either confirmed the user is on the latest package versions, or are assuming so in the absence of version information. This information may be useful in future steps.
4. Execution: we need to use a provided sandbox environment to actually execute and confirm the purported behavior. This will involve installing specific LangChain packages and configuring environment variables.
   1. We are provided a sandboxed Daytona container environment that is pre-loaded with the latest version of LangChain, its dependencies, and other packages such as `langchain-openai`.
   2. We are also provided code snippets extracted from the issue content in previous steps. We assume that these snippets are missing the necessary boilerplate code to run them successfully in the Daytona container. As a result, we must enrich the provided code snippets with the necessary boilerplate code to ensure they can run successfully in the Daytona container. This may involve adding import statements, setting up environment variables, or including any other necessary setup code. However, we do not infer any missing information that would change the behavior of the provided code snippets; we only add the necessary boilerplate to make them executable, and nothing else.
   3. Once we have the enriched code snippets ready, we proceed to execute them within the Daytona container environment. This step involves running the code and capturing any output, errors, or exceptions that occur during execution. The goal is to validate whether the provided code snippets reproduce the reported behavior as described in the issue. We save the full output to state for use in the next step.
5. Report generation: after executing the code snippets in the Daytona container, we analyze the output to determine whether the reported behavior was successfully reproduced. This involves comparing the actual output from the execution with the expected behavior as described in the issue. We then summarize our findings, including whether the issue was reproduced. This report is intended to assist maintainers in further investigating and addressing the reported issue. We save the generated report to state for use in subsequent steps.

Output: `validation_report.md` + `reproduction.py` (if successful)

## Implementation details

You may use any combination of LangChain, LangGraph, and Deep Agents.

Reference:

* <https://docs.langchain.com/oss/python/langchain/overview>
* <https://docs.langchain.com/oss/python/langgraph/overview>
* <https://docs.langchain.com/oss/python/deepagents/overview>

Note: this documentation is also available as an MCP tool for the entire LangChain docs site. These docs are also available locally at `../docs`.

Of particular interest for this project are the following sections:

* <https://docs.langchain.com/oss/python/langchain/multi-agent>
* <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>
* <https://docs.langchain.com/oss/python/langgraph/interrupts#approve-or-reject>
* <https://docs.langchain.com/oss/python/deepagents/cli#use-remote-sandboxes>
* <https://docs.langchain.com/oss/python/deepagents/backends#filesystembackend-local-disk>
* <https://docs.langchain.com/oss/python/langgraph/persistence>
* <https://docs.langchain.com/oss/python/langgraph/durable-execution>

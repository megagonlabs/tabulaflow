# Model setup

TabulaFlow supports hundreds of tool-capable models across more than 25 cloud
and local provider routes. It uses one model for the main conversation and
another for parallel subagent work. Most users only need to export one provider
API key and choose models in `/config`.

## Quick setup

Choose one provider and configure it before launching TabulaFlow:

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="your-api-key"
    tabulaflow
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="your-api-key"
    tabulaflow
    ```

=== "vLLM"

    ```bash
    export VLLM_BASE_URL="http://127.0.0.1:8000/v1"
    # For authenticated endpoints:
    # export VLLM_API_KEY="your-api-key"
    tabulaflow
    ```

TabulaFlow automatically selects models for OpenAI, Anthropic, and single-model
vLLM endpoints. Use `/config` to change them or select among multiple vLLM
models. Credentials are read from the environment and never saved.

!!! important "vLLM tool calling"
    TabulaFlow relies on automatic tool calling. Follow the current
    [vLLM tool-calling guide](https://docs.vllm.ai/en/stable/features/tool_calling/)
    to configure it for your model.

## Choose models

Run `/config` to choose the main model, subagent model, reasoning effort, and
maximum model request rate. The main model handles the conversation and plans
tool use; the subagent model handles parallel extraction, classification, and
other row-wise work.

Model identifiers use the Pydantic AI `provider:model` format:

```text
openai:gpt-5.6-sol
anthropic:claude-sonnet-5
vllm:Qwen/Qwen3-8B
```

The picker includes recommended models, the current selection, and compatible
models from the installed provider stack. You can also type a complete custom
identifier. TabulaFlow saves model selections in
`~/.tabulaflow/app_config.json`, but continues to read credentials from the
environment.

## Supported providers

The model picker includes models from all the provider routes below. TabulaFlow
uses Pydantic AI's environment variables and authentication unchanged; it does
not store these credentials. Set the listed variables before launching
TabulaFlow, then select a `provider:model` identifier in `/config` when
automatic setup does not apply.

### API key providers

| Provider | Prefix | Environment variable |
| --- | --- | --- |
| [OpenAI](https://pydantic.dev/docs/ai/models/openai/) | `openai:` | `OPENAI_API_KEY` |
| [Anthropic](https://pydantic.dev/docs/ai/models/anthropic/) | `anthropic:` | `ANTHROPIC_API_KEY` |
| [Google Gemini](https://pydantic.dev/docs/ai/models/google/) | `google:` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| [OpenRouter](https://pydantic.dev/docs/ai/models/openrouter/) | `openrouter:` | `OPENROUTER_API_KEY` |
| [DeepSeek](https://pydantic.dev/docs/ai/models/openai/#deepseek) | `deepseek:` | `DEEPSEEK_API_KEY` |
| [xAI](https://pydantic.dev/docs/ai/models/xai/) | `xai:` | `XAI_API_KEY` |
| [Groq](https://pydantic.dev/docs/ai/models/groq/) | `groq:` | `GROQ_API_KEY` |
| [Mistral](https://pydantic.dev/docs/ai/models/mistral/) | `mistral:` | `MISTRAL_API_KEY` |
| [Together AI](https://pydantic.dev/docs/ai/models/openai/#together-ai) | `together:` | `TOGETHER_API_KEY` |
| [Hugging Face](https://pydantic.dev/docs/ai/models/huggingface/) | `huggingface:` | `HF_TOKEN` |
| [Fireworks AI](https://pydantic.dev/docs/ai/models/openai/#fireworks-ai) | `fireworks:` | `FIREWORKS_API_KEY` |
| [Cohere](https://pydantic.dev/docs/ai/models/cohere/) | `cohere:` | `CO_API_KEY` |
| [Cerebras](https://pydantic.dev/docs/ai/models/cerebras/) | `cerebras:` | `CEREBRAS_API_KEY` |
| [Alibaba Cloud Model Studio](https://pydantic.dev/docs/ai/models/openai/#alibaba-cloud-model-studio-dashscope) | `alibaba:` | `ALIBABA_API_KEY` or `DASHSCOPE_API_KEY` |
| [Moonshot AI](https://pydantic.dev/docs/ai/models/openai/#moonshotai) | `moonshotai:` | `MOONSHOTAI_API_KEY` |
| [Nebius AI Studio](https://pydantic.dev/docs/ai/models/openai/#nebius-ai-studio) | `nebius:` | `NEBIUS_API_KEY` |
| [Z.AI](https://pydantic.dev/docs/ai/models/zai/) | `zai:` | `ZAI_API_KEY` |
| [Crusoe](https://pydantic.dev/docs/ai/models/crusoe/) | `crusoe:` | `CRUSOE_API_KEY` |
| [OVHcloud AI Endpoints](https://pydantic.dev/docs/ai/models/openai/#ovhcloud-ai-endpoints) | `ovhcloud:` | `OVHCLOUD_API_KEY` |

### Cloud and hosted authentication

| Provider | Prefix | Authentication |
| --- | --- | --- |
| [Amazon Bedrock](https://pydantic.dev/docs/ai/models/bedrock/) | `bedrock:` | AWS credential chain and `AWS_DEFAULT_REGION`, or `AWS_BEARER_TOKEN_BEDROCK` |
| [Azure OpenAI](https://pydantic.dev/docs/ai/models/openai/#azure-ai-foundry) | `azure:` | `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT`; `OPENAI_API_VERSION` for versioned endpoints |
| [Google Cloud](https://pydantic.dev/docs/ai/models/google/) | `google-cloud:` | Application Default Credentials with `GOOGLE_CLOUD_PROJECT` and optional `GOOGLE_CLOUD_LOCATION`; or `GOOGLE_API_KEY` for Vertex AI Express Mode |
| [GitHub Copilot](https://pydantic.dev/docs/ai/models/github-copilot/) | `github-copilot:` | `GITHUB_COPILOT_API_KEY`, `GITHUB_COPILOT_API_TOKEN`, or `COPILOT_GITHUB_TOKEN` |
| [Vercel AI Gateway](https://pydantic.dev/docs/ai/models/openai/#vercel-ai-gateway) | `vercel:` | `VERCEL_AI_GATEWAY_API_KEY` or `VERCEL_OIDC_TOKEN` |
| [Snowflake Cortex](https://pydantic.dev/docs/ai/models/snowflake/) | `snowflake:` | `SNOWFLAKE_ACCOUNT` and `SNOWFLAKE_TOKEN` |

### Local and custom endpoints

| Provider | Prefix | Connection settings |
| --- | --- | --- |
| [Ollama](https://pydantic.dev/docs/ai/models/ollama/) | `ollama:` | `OLLAMA_BASE_URL`; optional `OLLAMA_API_KEY` |
| [vLLM](https://pydantic.dev/docs/ai/models/openai/#vllm) | `vllm:` | `VLLM_BASE_URL`; optional `VLLM_API_KEY` |

Provider requirements can change independently of TabulaFlow. Follow the
linked Pydantic AI provider page for account setup and provider-specific
details. If a required setting is missing, TabulaFlow names it when model
activation fails.

## Model requirements

The Data Agent sends instructions and tool schemas and expects models to
produce dependable tool calls. Choose models with:

- Text generation and tool-calling support
- A large context window
- Reliable structured output for extraction and subagent work

Disabling the LLM in `/config` turns off conversational analysis while keeping
data connections and the data explorer available.

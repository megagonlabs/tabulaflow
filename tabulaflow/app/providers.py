"""Provider metadata shared by model discovery and configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    """User-facing metadata for one Pydantic AI provider route."""

    id: str
    name: str
    catalog_ids: tuple[str, ...] = ()
    api_key_vars: tuple[str, ...] = ()


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec("openai", "OpenAI", ("openai",), ("OPENAI_API_KEY",)),
    ProviderSpec("anthropic", "Anthropic", ("anthropic",), ("ANTHROPIC_API_KEY",)),
    ProviderSpec("google", "Google Gemini", ("google",), ("GOOGLE_API_KEY", "GEMINI_API_KEY")),
    ProviderSpec("deepseek", "DeepSeek", ("deepseek",), ("DEEPSEEK_API_KEY",)),
    ProviderSpec("openrouter", "OpenRouter", ("openrouter",), ("OPENROUTER_API_KEY",)),
    ProviderSpec("vercel", "Vercel AI Gateway", ("vercel",)),
    ProviderSpec("azure", "Azure OpenAI", ("azure",)),
    ProviderSpec("google-cloud", "Google Cloud", ("google-vertex", "google-vertex-anthropic")),
    ProviderSpec("bedrock", "Amazon Bedrock", ("amazon-bedrock",)),
    ProviderSpec("groq", "Groq", ("groq",), ("GROQ_API_KEY",)),
    ProviderSpec("mistral", "Mistral", ("mistral",), ("MISTRAL_API_KEY",)),
    ProviderSpec("cerebras", "Cerebras", ("cerebras",), ("CEREBRAS_API_KEY",)),
    ProviderSpec("cohere", "Cohere", ("cohere",), ("CO_API_KEY",)),
    ProviderSpec("crusoe", "Crusoe", ("crusoe",), ("CRUSOE_API_KEY",)),
    ProviderSpec("xai", "xAI", ("xai",), ("XAI_API_KEY",)),
    ProviderSpec("moonshotai", "Moonshot AI", ("moonshotai",), ("MOONSHOTAI_API_KEY",)),
    ProviderSpec("fireworks", "Fireworks AI", ("fireworks-ai",), ("FIREWORKS_API_KEY",)),
    ProviderSpec("together", "Together AI", ("togetherai",), ("TOGETHER_API_KEY",)),
    ProviderSpec("huggingface", "Hugging Face", ("huggingface",), ("HF_TOKEN",)),
    ProviderSpec("github-copilot", "GitHub Copilot", ("github-copilot",)),
    ProviderSpec("nebius", "Nebius AI Studio", ("nebius",), ("NEBIUS_API_KEY",)),
    ProviderSpec("ovhcloud", "OVHcloud AI Endpoints", ("ovhcloud",), ("OVHCLOUD_API_KEY",)),
    ProviderSpec("alibaba", "Alibaba Cloud Model Studio", ("alibaba",), ("ALIBABA_API_KEY", "DASHSCOPE_API_KEY")),
    ProviderSpec("snowflake", "Snowflake Cortex", ("snowflake-cortex",)),
    ProviderSpec("zai", "Z.AI", ("zai",), ("ZAI_API_KEY",)),
    ProviderSpec("ollama", "Ollama", ("ollama-cloud",)),
    ProviderSpec("vllm", "vLLM"),
)

_PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDER_SPECS}


def provider_spec(provider_id: str) -> ProviderSpec:
    """Return metadata for a provider prefix."""
    return _PROVIDER_BY_ID.get(provider_id, ProviderSpec(provider_id, provider_id))

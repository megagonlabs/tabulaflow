from pydantic_ai.models.openai import OpenAIModel


def get_pydantic_ai_llm(litellm_id: str):
    provider, model = litellm_id.split("/", 1)
    if provider == "openai":
        return OpenAIModel(model_name=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

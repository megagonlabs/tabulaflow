from mintq.config import mintq_config
from mintq.schema import Usage

LLMS = [
    "openai:gpt-4.1",
    "openai-responses:gpt-4.1",
    "fireworks:accounts/fireworks/models/deepseek-r1-0528",
    "google-vertex:gemini-2.0-flash",
    "anthropic:claude-sonnet-4-5-20250929",
    "fireworks:accounts/fireworks/models/qwen3-235b-a22b-thinking-2507",
    "fireworks:accounts/fireworks/models/gpt-oss-120b",
    "fireworks:accounts/fireworks/models/llama-v3p1-405b-instruct",
    "fireworks:accounts/fireworks/models/kimi-k2-instruct",
]


def main():
    mintq_config.setup_logging()
    for llm in LLMS:
        print(llm)
        usage = Usage.create(llm, 1, 1000000, 1000000)
        if usage.api_cost_usd == 0:
            print(f"Warning: API cost for {llm} is 0.0. API cost calculation might not be supported for {llm}.")
        else:
            print(usage.api_cost_usd)


if __name__ == "__main__":
    main()

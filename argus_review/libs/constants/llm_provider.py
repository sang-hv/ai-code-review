from enum import StrEnum


class LLMProvider(StrEnum):
    OPENAI = "OPENAI"
    GEMINI = "GEMINI"
    CLAUDE = "CLAUDE"
    OLLAMA = "OLLAMA"
    BEDROCK = "BEDROCK"
    OPENROUTER = "OPENROUTER"
    AZURE_OPENAI = "AZURE_OPENAI"

    # Generic OpenAI-compatible endpoint (LMRouter, vLLM, LocalAI, LiteLLM, ...).
    # Only api_url + model (and optional api_token) are required.
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"

    # 9Router local proxy (https://9router.com) — an OpenAI-compatible gateway.
    # Same client as OPENAI_COMPATIBLE, but api_url defaults to the local proxy.
    NINE_ROUTER = "9ROUTER"

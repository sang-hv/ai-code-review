from argus_review.clients.openai.v1.schema import OpenAIChatRequestSchema, OpenAIMessageSchema
from argus_review.clients.openai_compatible.client import get_openai_compatible_http_client
from argus_review.config import settings
from argus_review.services.llm.types import ChatResultSchema, LLMClientProtocol


class OpenAICompatibleLLMClient(LLMClientProtocol):
    """
    Client for any OpenAI Chat Completions compatible endpoint.

    Shared by the OPENAI_COMPATIBLE and 9ROUTER providers — they only differ in
    their default configuration (api_url), not in wire behaviour.
    """

    def __init__(self):
        self.meta = settings.llm.meta
        self.http_client = get_openai_compatible_http_client()

    async def chat(self, prompt: str, prompt_system: str) -> ChatResultSchema:
        request = OpenAIChatRequestSchema(
            model=self.meta.model,
            messages=[
                OpenAIMessageSchema(role="system", content=prompt_system),
                OpenAIMessageSchema(role="user", content=prompt),
            ],
            max_tokens=self.meta.max_tokens,
            temperature=self.meta.temperature,
        )
        response = await self.http_client.chat(request)
        return ChatResultSchema(
            text=response.first_text,
            total_tokens=response.usage.total_tokens,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

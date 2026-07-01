from typing import Protocol

from argus_review.clients.openrouter.schema import (
    OpenRouterChatRequestSchema,
    OpenRouterChatResponseSchema
)


class OpenRouterHTTPClientProtocol(Protocol):
    async def chat(self, request: OpenRouterChatRequestSchema) -> OpenRouterChatResponseSchema:
        ...

from typing import Protocol

from argus_review.clients.ollama.schema import OllamaChatRequestSchema, OllamaChatResponseSchema


class OllamaHTTPClientProtocol(Protocol):
    async def chat(self, request: OllamaChatRequestSchema) -> OllamaChatResponseSchema:
        ...

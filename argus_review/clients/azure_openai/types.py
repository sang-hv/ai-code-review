from typing import Protocol

from argus_review.clients.azure_openai.schema import AzureOpenAIChatRequestSchema, AzureOpenAIChatResponseSchema


class AzureOpenAIHTTPClientProtocol(Protocol):
    async def chat(self, request: AzureOpenAIChatRequestSchema) -> AzureOpenAIChatResponseSchema:
        ...

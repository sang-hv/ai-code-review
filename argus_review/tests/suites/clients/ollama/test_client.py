import pytest
from httpx import AsyncClient

from argus_review.clients.ollama.client import get_ollama_http_client, OllamaHTTPClient


@pytest.mark.usefixtures('ollama_http_client_config')
def test_get_ollama_http_client_builds_ok():
    ollama_http_client = get_ollama_http_client()

    assert isinstance(ollama_http_client, OllamaHTTPClient)
    assert isinstance(ollama_http_client.client, AsyncClient)

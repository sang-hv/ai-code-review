import pytest

from argus_review.services.hook import HookService


@pytest.fixture
def hook_service() -> HookService:
    return HookService()

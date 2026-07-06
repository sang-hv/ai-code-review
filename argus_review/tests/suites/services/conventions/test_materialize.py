import pytest

from argus_review.config import settings
from argus_review.services.conventions.schema import ResolvedConventionSchema
from argus_review.services.conventions.service import ConventionsService


def _service_with_docs(docs: list[ResolvedConventionSchema]) -> ConventionsService:
    service = ConventionsService()
    service._cached_docs = docs
    return service


def test_materialize_writes_docs_and_returns_inventory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    cache = tmp_path / "conv"
    monkeypatch.setattr(settings.conventions, "enabled", True)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(cache))

    service = _service_with_docs([ResolvedConventionSchema(name="docs/py.md", content="a\nb\nc")])
    inventory = service.materialize("inline")

    assert "docs/py.md" in inventory
    assert "3 lines" in inventory

    written = list(cache.glob("*.md"))
    assert len(written) == 1
    assert written[0].read_text(encoding="utf-8") == "a\nb\nc"
    assert (cache / ".source-hash").exists()


def test_materialize_returns_empty_when_disabled(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.conventions, "enabled", False)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(tmp_path / "conv"))

    service = _service_with_docs([ResolvedConventionSchema(name="docs/py.md", content="x")])
    assert service.materialize("inline") == ""


def test_materialize_returns_empty_when_mode_disabled(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.conventions, "enabled", True)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(tmp_path / "conv"))
    monkeypatch.setattr(settings.conventions.modes, "inline", False)

    service = _service_with_docs([ResolvedConventionSchema(name="docs/py.md", content="x")])
    assert service.materialize("inline") == ""


def test_materialize_returns_empty_when_no_docs(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings.conventions, "enabled", True)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(tmp_path / "conv"))

    service = _service_with_docs([])
    assert service.materialize("inline") == ""


def test_materialize_skips_rewrite_when_hash_unchanged(tmp_path, monkeypatch: pytest.MonkeyPatch):
    cache = tmp_path / "conv"
    monkeypatch.setattr(settings.conventions, "enabled", True)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(cache))

    docs = [ResolvedConventionSchema(name="docs/py.md", content="a\nb\nc")]
    _service_with_docs(docs).materialize("inline")

    written = next(cache.glob("*.md"))
    written.write_text("SENTINEL", encoding="utf-8")

    # Same content hash → second run must not overwrite the materialized file.
    _service_with_docs(docs).materialize("inline")
    assert written.read_text(encoding="utf-8") == "SENTINEL"


def test_materialize_rewrites_when_content_changes(tmp_path, monkeypatch: pytest.MonkeyPatch):
    cache = tmp_path / "conv"
    monkeypatch.setattr(settings.conventions, "enabled", True)
    monkeypatch.setattr(settings.conventions, "cache_dir", str(cache))

    _service_with_docs([ResolvedConventionSchema(name="docs/py.md", content="old")]).materialize("inline")
    _service_with_docs([ResolvedConventionSchema(name="docs/py.md", content="new-content")]).materialize("inline")

    written = next(cache.glob("*.md"))
    assert written.read_text(encoding="utf-8") == "new-content"

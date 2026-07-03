from pathlib import Path

import pytest

from argus_review.config import settings
from argus_review.libs.config.conventions import (
    ConventionModesConfig,
    ConventionsConfig,
    LocalConventionSource,
    UrlConventionSource,
)
from argus_review.services.conventions.schema import ResolvedConventionSchema
from argus_review.services.conventions.service import ConventionsService


def _write_doc(tmp_path: Path, content: str = "RULE") -> LocalConventionSource:
    doc = tmp_path / "style.md"
    doc.write_text(content, encoding="utf-8")
    return LocalConventionSource(path=str(doc))


def test_render_returns_empty_when_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(enabled=False, sources=[_write_doc(tmp_path)]),
    )
    assert ConventionsService().render("inline") == ""


def test_render_returns_empty_when_mode_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(
            enabled=True,
            sources=[_write_doc(tmp_path)],
            modes=ConventionModesConfig(summary=False),
        ),
    )
    service = ConventionsService()
    assert service.render("summary") == ""
    assert "RULE" in service.render("inline")


def test_render_builds_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(enabled=True, heading="My Standards", sources=[_write_doc(tmp_path, "USE_SNAKE_CASE")]),
    )
    block = ConventionsService().render("inline")

    assert block.startswith("## My Standards")
    assert "### style.md" in block
    assert "USE_SNAKE_CASE" in block


def test_render_returns_empty_when_no_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(enabled=True, sources=[LocalConventionSource(path=str(tmp_path / "missing.md"))]),
    )
    assert ConventionsService().render("inline") == ""


def test_resolution_is_cached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(enabled=True, sources=[_write_doc(tmp_path)]),
    )

    calls = {"count": 0}

    def counting_resolve_local(source):
        calls["count"] += 1
        return [ResolvedConventionSchema(name="style.md", content="RULE")]

    monkeypatch.setattr(
        "argus_review.services.conventions.service.resolve_local",
        counting_resolve_local,
    )

    service = ConventionsService()
    service.render("inline")
    service.render("summary")
    service.render("context")

    assert calls["count"] == 1


def test_resolution_is_fail_soft(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(
        settings, "conventions",
        ConventionsConfig(
            enabled=True,
            sources=[
                _write_doc(tmp_path, "GOOD_RULE"),
                UrlConventionSource(url="https://example.com/broken.md"),
            ],
        ),
    )

    def boom(source, timeout):
        raise RuntimeError("network down")

    monkeypatch.setattr("argus_review.services.conventions.service.resolve_url", boom)

    block = ConventionsService().render("inline")
    assert "GOOD_RULE" in block  # the healthy source still made it in

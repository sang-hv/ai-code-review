import subprocess
from pathlib import Path

import httpx
import pytest
from pydantic import HttpUrl, SecretStr

from argus_review.libs.config.conventions import (
    GitConventionSource,
    LocalConventionSource,
    UrlConventionSource,
)
from argus_review.services.conventions.sources import (
    _inject_git_token,
    resolve_git,
    resolve_local,
    resolve_url,
)


# ---------- local ----------

def test_resolve_local_single_file(tmp_path: Path):
    doc = tmp_path / "style.md"
    doc.write_text("RULE_A", encoding="utf-8")

    docs = resolve_local(LocalConventionSource(path=str(doc)))
    assert len(docs) == 1
    assert docs[0].name == "style.md"
    assert docs[0].content == "RULE_A"


def test_resolve_local_directory_glob(tmp_path: Path):
    (tmp_path / "a.md").write_text("A", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.md").write_text("B", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("SKIP", encoding="utf-8")

    docs = resolve_local(LocalConventionSource(path=str(tmp_path)))
    contents = {doc.content for doc in docs}
    assert contents == {"A", "B"}


def test_resolve_local_missing_path_returns_empty(tmp_path: Path):
    docs = resolve_local(LocalConventionSource(path=str(tmp_path / "nope")))
    assert docs == []


# ---------- url ----------

def test_resolve_url_success(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        captured["url"] = url
        captured["headers"] = headers
        return httpx.Response(200, text="URL_CONTENT", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    source = UrlConventionSource(url=HttpUrl("https://example.com/style.md"), token=SecretStr("abc"))
    docs = resolve_url(source, timeout=5)

    assert len(docs) == 1
    assert docs[0].content == "URL_CONTENT"
    assert captured["headers"]["Authorization"] == "Bearer abc"


def test_resolve_url_without_token_sends_no_auth(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_get(url, headers=None, timeout=None, follow_redirects=None):
        captured["headers"] = headers
        return httpx.Response(200, text="X", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    resolve_url(UrlConventionSource(url=HttpUrl("https://example.com/style.md")), timeout=5)
    assert "Authorization" not in captured["headers"]


# ---------- git ----------

def test_inject_git_token_https():
    result = _inject_git_token("https://github.com/org/repo.git", "secret")
    assert result == "https://x-access-token:secret@github.com/org/repo.git"


def test_inject_git_token_noop_without_token():
    assert _inject_git_token("https://github.com/org/repo.git", None) == "https://github.com/org/repo.git"


def test_inject_git_token_noop_for_ssh():
    assert _inject_git_token("git@github.com:org/repo.git", "secret") == "git@github.com:org/repo.git"


def test_resolve_git_reads_markdown(monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, check, capture_output, timeout):
        dest = Path(cmd[-1])
        (dest / "conv.md").write_text("GIT_RULE", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    source = GitConventionSource(repo="https://github.com/org/standards.git", ref="main")
    docs = resolve_git(source, timeout=5)

    assert len(docs) == 1
    assert docs[0].content == "GIT_RULE"
    assert docs[0].name.startswith("https://github.com/org/standards.git@main:")


def test_resolve_git_missing_subpath_returns_empty(monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, check, capture_output, timeout):
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    source = GitConventionSource(repo="https://github.com/org/standards.git", path="does/not/exist")
    assert resolve_git(source, timeout=5) == []

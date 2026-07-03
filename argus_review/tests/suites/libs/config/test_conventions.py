from argus_review.libs.config.conventions import (
    ConventionsConfig,
    ConventionModesConfig,
    GitConventionSource,
    LocalConventionSource,
    UrlConventionSource,
)


def test_conventions_config_defaults():
    config = ConventionsConfig()
    assert config.enabled is False
    assert config.heading == "Project Coding Conventions"
    assert config.timeout == 30
    assert config.sources == []


def test_convention_modes_default_all_enabled():
    modes = ConventionModesConfig()
    for mode in ("inline", "context", "summary", "inline_reply", "summary_reply"):
        assert modes.is_enabled(mode) is True


def test_convention_modes_is_enabled_respects_toggle():
    modes = ConventionModesConfig(summary=False)
    assert modes.is_enabled("summary") is False
    assert modes.is_enabled("inline") is True


def test_convention_modes_unknown_mode_defaults_true():
    assert ConventionModesConfig().is_enabled("does_not_exist") is True


def test_sources_are_parsed_by_discriminator():
    config = ConventionsConfig(
        enabled=True,
        sources=[
            {"type": "local", "path": "./docs/conventions"},
            {"type": "url", "url": "https://example.com/style.md", "token": "url-token"},
            {"type": "git", "repo": "https://github.com/org/standards.git", "path": "python", "token": "git-token"},
        ],
    )

    local, url, git = config.sources
    assert isinstance(local, LocalConventionSource)
    assert local.path == "./docs/conventions"
    assert local.glob == "**/*.md"

    assert isinstance(url, UrlConventionSource)
    assert url.token.get_secret_value() == "url-token"

    assert isinstance(git, GitConventionSource)
    assert git.repo == "https://github.com/org/standards.git"
    assert git.ref == "main"
    assert git.token.get_secret_value() == "git-token"

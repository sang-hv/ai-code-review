import tomllib
from pathlib import Path


def load_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def test_distribution_identity_is_argusreview():
    pyproject = load_pyproject()

    assert pyproject["project"]["name"] == "argus-review-code"
    assert pyproject["project"]["scripts"] == {
        "argus-review": "argus_review.cli.main:app",
    }


def test_setuptools_discovers_argusreview_package_data():
    pyproject = load_pyproject()

    assert pyproject["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "argus_review*",
    ]
    assert pyproject["tool"]["setuptools"]["package-data"] == {
        "argus_review.prompts": ["*.md"],
        "argus_review.resources": ["*.yaml"],
    }

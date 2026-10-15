from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_aligned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    package_init = (
        ROOT / "src" / "grocery_delivery_availability" / "__init__.py"
    ).read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    citation_version = rf'^version: ["\']?{re.escape(version)}["\']?$'
    assert re.search(citation_version, citation, re.MULTILINE)
    assert f'__version__ = "{version}"' in package_init
    assert f"## [{version}]" in changelog


def test_citation_metadata_respects_release_authorship() -> None:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    assert 'date-released: "2026-10-15"' in citation
    assert 'family-names: "Xiao"' in citation
    assert 'given-names: "Chenrui"' in citation
    assert 'doi: "10.5281/zenodo.23400413"' in citation
    assert 'value: "10.5281/zenodo.23400412"' in citation
    assert "email:" not in citation
    assert "orcid:" not in citation

"""Tests for DocumentTree loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_tree.tree import (
    DocumentTree,
    DocumentTreeError,
    slug_from_title,
)


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_slug_from_title() -> None:
    assert slug_from_title("Models at a glance") == (
        "models-at-a-glance"
    )
    assert slug_from_title("Command R+") == "command-r"


def test_url_without_filename_uses_title(tmp_path: Path) -> None:
    structure = write_yaml(
        tmp_path / "guide.yaml",
        "Overview: https://example.com/docs/\n",
    )
    tree = DocumentTree.from_yaml(structure)
    assert tree.roots[0].directory == "overview"
    assert tree.roots[0].url == "https://example.com/docs/"


def test_local_page_omits_url(tmp_path: Path) -> None:
    structure = write_yaml(
        tmp_path / "guide.yaml",
        """
Notes:
  local: true
  Detail:
    local: true
""",
    )
    tree = DocumentTree.from_yaml(structure)
    notes = tree.roots[0]
    assert notes.local is True
    assert notes.url is None
    assert notes.directory == "notes"
    assert notes.children[0].title == "Detail"
    assert notes.children[0].url is None


def test_loads_leaf_and_parent(tmp_path: Path) -> None:
    structure = write_yaml(
        tmp_path / "guide.yaml",
        """
Overview: https://example.com/overview.md
Models:
  url: https://example.com/models.md
  Alpha: https://example.com/alpha.md
""",
    )
    tree = DocumentTree.from_yaml(structure)
    assert tree.page_count() == 3
    assert tree.max_depth() == 2
    assert tree.roots[0].title == "Overview"
    assert tree.roots[1].children[0].directory == "alpha"


def test_rejects_missing_url(tmp_path: Path) -> None:
    structure = write_yaml(
        tmp_path / "bad.yaml",
        """
Models:
  Alpha: https://example.com/alpha.md
""",
    )
    with pytest.raises(DocumentTreeError, match="Missing url"):
        DocumentTree.from_yaml(structure)


def test_rejects_sibling_directory_collision(tmp_path: Path) -> None:
    structure = write_yaml(
        tmp_path / "bad.yaml",
        """
One: https://example.com/same.md
same-page: https://example.com/path/same-page.md
Same Page: https://example.com/other.md
""",
    )
    with pytest.raises(DocumentTreeError, match="share directory"):
        DocumentTree.from_yaml(structure)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DocumentTreeError, match="not found"):
        DocumentTree.from_yaml(tmp_path / "missing.yaml")

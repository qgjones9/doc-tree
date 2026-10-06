"""Tests for DocumentTree loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_tree.tree import DocumentTree, DocumentTreeError


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_directory_from_url_strips_md_and_html() -> None:
    assert (
        DocumentTree.directory_from_url(
            "https://example.com/a/overview.md"
        )
        == "overview"
    )
    assert (
        DocumentTree.directory_from_url(
            "https://example.com/a/model.html"
        )
        == "model"
    )


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
Two: https://example.com/path/same.md
""",
    )
    with pytest.raises(DocumentTreeError, match="share directory"):
        DocumentTree.from_yaml(structure)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DocumentTreeError, match="not found"):
        DocumentTree.from_yaml(tmp_path / "missing.yaml")

"""Tests for NavInserter surgical updates."""

from __future__ import annotations

from pathlib import Path

from doc_tree.nav import NavInserter
from doc_tree.tree import DocumentTree


def test_insert_replaces_leaf_parent(tmp_path: Path) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(
        """
Overview: https://example.com/overview.md
Models:
  url: https://example.com/models.md
  Alpha: https://example.com/alpha.md
""",
        encoding="utf-8",
    )
    tree = DocumentTree.from_yaml(structure)
    nav_file = tmp_path / "mkdocs.yml"
    nav_file.write_text(
        """site_name: Demo
nav:
  - Home: index.md
  - Service: service/index.md
  - Other: other/index.md
""",
        encoding="utf-8",
    )
    NavInserter(
        tree,
        nav_file,
        "Service",
        docs_prefix="service/user-guide",
        section_title="User Guide",
    ).insert()
    text = nav_file.read_text(encoding="utf-8")
    assert "site_name: Demo" in text
    assert "- Service:" in text
    assert "- Service: service/index.md" in text
    assert "- User Guide:" in text
    assert (
        "- User Guide: service/user-guide/index.md" in text
    )
    assert "- Overview: service/user-guide/overview/index.md" in text
    assert "- Other: other/index.md" in text

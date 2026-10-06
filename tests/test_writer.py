"""Tests for TreeWriter dry-run and file creation."""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_tree.tree import DocumentTree
from doc_tree.writer import TreeWriter, TreeWriterError


SAMPLE = """
Overview: https://example.com/overview.md
Models:
  url: https://example.com/models.md
  Alpha: https://example.com/alpha.md
"""


def test_plan_reports_counts(tmp_path: Path) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(SAMPLE, encoding="utf-8")
    tree = DocumentTree.from_yaml(structure)
    output = tmp_path / "out"
    plan = TreeWriter(
        tree,
        output,
        section_title="Guide",
        section_url="https://example.com/",
    ).plan()
    assert plan.page_count == 4
    assert plan.max_depth == 3
    assert not output.exists()


def test_write_creates_pages(tmp_path: Path) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(SAMPLE, encoding="utf-8")
    tree = DocumentTree.from_yaml(structure)
    output = tmp_path / "out"
    TreeWriter(
        tree,
        output,
        section_title="Guide",
        section_url="https://example.com/",
    ).write()
    section = (output / "index.md").read_text(encoding="utf-8")
    assert "# [Guide](https://example.com/)" in section
    overview = (
        output / "overview" / "index.md"
    ).read_text(encoding="utf-8")
    assert "# [Overview](https://example.com/overview.md)" in overview
    models = (output / "models" / "index.md").read_text(
        encoding="utf-8"
    )
    assert "- [Alpha](alpha/index.md)" in models


def test_write_refuses_overwrite_without_force(tmp_path: Path) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(
        "Overview: https://example.com/overview.md\n",
        encoding="utf-8",
    )
    tree = DocumentTree.from_yaml(structure)
    output = tmp_path / "out"
    writer = TreeWriter(tree, output)
    writer.write()
    with pytest.raises(TreeWriterError, match="--force"):
        writer.write()
    TreeWriter(tree, output, force=True).write()

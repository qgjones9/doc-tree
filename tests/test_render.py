"""Tests for PageRenderer output."""

from __future__ import annotations

from doc_tree.render import PageRenderer
from doc_tree.tree import DocumentNode


def test_render_leaf() -> None:
    node = DocumentNode(
        title="Overview",
        url="https://example.com/overview.md",
        directory="overview",
    )
    text = PageRenderer().render(node)
    assert text == (
        "# [Overview](https://example.com/overview.md)\n\n"
    )


def test_render_parent_lists_children() -> None:
    child = DocumentNode(
        title="Alpha",
        url="https://example.com/alpha.md",
        directory="alpha",
    )
    parent = DocumentNode(
        title="Models",
        url="https://example.com/models.md",
        directory="models",
        children=[child],
    )
    text = PageRenderer().render(parent)
    assert "# [Models](https://example.com/models.md)" in text
    assert "## Child pages" in text
    assert "- [Alpha](alpha/index.md)" in text
    assert text.index("## Child pages") < text.index("- [Alpha]")


def test_render_local_page_without_url() -> None:
    node = DocumentNode(
        title="A note I wrote",
        url=None,
        directory="a-note-i-wrote",
        local=True,
    )
    text = PageRenderer().render(node)
    assert text == (
        "---\nlocal: true\n---\n# A note I wrote\n\n"
    )
    child = DocumentNode(
        title="Overview",
        url="https://example.com/overview.md",
        directory="overview",
    )
    text = PageRenderer().render_section(
        "Example Guide",
        "https://example.com/docs/",
        [child],
    )
    assert text.startswith(
        "# [Example Guide](https://example.com/docs/)"
    )
    assert "## Child pages" in text
    assert "- [Overview](overview/index.md)" in text

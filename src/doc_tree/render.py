"""Render index.md text for documentation pages."""

from __future__ import annotations

from doc_tree.tree import DocumentNode


class PageRenderer:
    """Build markdown text for a documentation page."""

    def render(self, node: DocumentNode) -> str:
        """Render a page heading and optional child links.

        Args:
            node: Page to render.

        Returns:
            Markdown text ending with a blank line.
        """
        parts: list[str] = []
        if node.local and not node.url:
            parts.append("---\nlocal: true\n---\n")
            parts.append(f"# {node.title}\n\n")
        else:
            if not node.url:
                raise ValueError(f"Page is missing a URL: {node.title}")
            parts.append(f"# [{node.title}]({node.url})\n\n")
        if node.children:
            for child in node.children:
                href = f"{child.directory}/index.md"
                parts.append(f"- [{child.title}]({href})\n")
            parts.append("\n")
        return "".join(parts)

    def render_section(
        self,
        title: str,
        url: str,
        children: list[DocumentNode],
    ) -> str:
        """Render the section index that wraps YAML roots.

        Args:
            title: Section display title.
            url: Canonical section URL.
            children: Top-level pages from the YAML tree.

        Returns:
            Markdown text ending with a blank line.
        """
        parts = [f"# [{title}]({url})\n\n"]
        for child in children:
            href = f"{child.directory}/index.md"
            parts.append(f"- [{child.title}]({href})\n")
        parts.append("\n")
        return "".join(parts)

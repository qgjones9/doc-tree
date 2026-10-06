"""Insert a documentation tree into an MkDocs nav list."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from doc_tree.tree import DocumentNode, DocumentTree


class NavInserterError(RuntimeError):
    """Raised when an MkDocs nav file cannot be updated."""


class NavInserter:
    """Insert a scaffolded tree under an existing nav parent.

    The update is surgical: only the matched parent entry is rewritten.
    Comments and other keys in the MkDocs config stay as they were.
    """

    def __init__(
        self,
        tree: DocumentTree,
        nav_file: Path,
        nav_parent: str,
        *,
        docs_prefix: str,
        section_title: str | None = None,
    ) -> None:
        """Configure a nav insert for one MkDocs config.

        Args:
            tree: Validated documentation tree.
            nav_file: Path to ``mkdocs.yml``.
            nav_parent: Existing nav item title that receives the tree.
            docs_prefix: Path prefix relative to the MkDocs docs_dir,
                such as ``amazon-web-services/.../user-guide``.
            section_title: Optional section title listed under the
                parent. The section index is ``docs_prefix/index.md``.
        """
        self._tree = tree
        self._nav_file = nav_file
        self._nav_parent = nav_parent
        self._docs_prefix = docs_prefix.strip("/")
        self._section_title = section_title

    def build_entries(self) -> list[dict[str, Any]]:
        """Build the nested nav entries for the tree."""
        if self._section_title is not None:
            section_path = f"{self._docs_prefix}/index.md"
            children = [
                self._node_entry(root, self._docs_prefix)
                for root in self._tree.roots
            ]
            return [
                {
                    self._section_title: [
                        {self._section_title: section_path},
                        *children,
                    ]
                }
            ]
        return [
            self._node_entry(root, self._docs_prefix)
            for root in self._tree.roots
        ]

    def insert(self) -> None:
        """Replace a leaf nav parent with a nested section.

        Raises:
            NavInserterError: The parent entry cannot be found or the
                file cannot be updated safely.
        """
        if not self._nav_file.is_file():
            raise NavInserterError(
                f"Nav file not found: {self._nav_file}"
            )
        text = self._nav_file.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"^([ \t]*)- {re.escape(self._nav_parent)}: "
            rf"([^\n]+)\n",
            re.MULTILINE,
        )
        match = pattern.search(text)
        if match is None:
            raise NavInserterError(
                f"Nav parent leaf not found: {self._nav_parent}"
            )
        indent = match.group(1)
        parent_path = match.group(2).strip()
        if not parent_path.endswith(".md"):
            raise NavInserterError(
                f"Nav parent is not a leaf path: {self._nav_parent}"
            )
        block = self._render_parent_block(indent, parent_path)
        updated = text[: match.start()] + block + text[match.end() :]
        self._nav_file.write_text(updated, encoding="utf-8")

    def _node_entry(
        self,
        node: DocumentNode,
        prefix: str,
    ) -> dict[str, Any]:
        path = f"{prefix}/{node.directory}/index.md"
        if not node.children:
            return {node.title: path}
        children = [
            self._node_entry(child, f"{prefix}/{node.directory}")
            for child in node.children
        ]
        return {node.title: [{node.title: path}, *children]}

    def _render_parent_block(
        self,
        indent: str,
        parent_path: str,
    ) -> str:
        child_indent_unit = "  "
        nested = [
            {self._nav_parent: parent_path},
            *self.build_entries(),
        ]
        dumped = yaml.safe_dump(
            nested,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
            default_flow_style=False,
        )
        lines = [f"{indent}- {self._nav_parent}:"]
        for line in dumped.splitlines():
            if not line.strip():
                continue
            lines.append(f"{indent}{child_indent_unit}{line}")
        return "\n".join(lines) + "\n"

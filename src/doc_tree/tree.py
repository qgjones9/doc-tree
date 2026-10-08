"""Load and validate a title-and-URL documentation tree."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class DocumentTreeError(ValueError):
    """Raised when a YAML document tree fails the contract."""


def slug_from_title(title: str) -> str:
    """Return the directory slug for a page title.

    Lowercase the title, turn each run of non-alphanumeric characters
    into one hyphen, and strip hyphens from the ends.

    Args:
        title: Page title from YAML or an H1.

    Returns:
        Directory name. Empty when the title has no letters or digits.
    """
    lowered = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered)
    return slug.strip("-")


@dataclass(slots=True)
class DocumentNode:
    """One documentation page in the tree.

    Attributes:
        title: Display title for the page heading and nav.
        url: Canonical URL for the page. Absent for a local page.
        directory: Directory name derived from the title slug.
        local: True when the page does not require a source URL.
        children: Direct child pages in YAML order.
    """

    title: str
    url: str | None
    directory: str
    local: bool = False
    children: list[DocumentNode] = field(default_factory=list)

    @property
    def is_leaf(self) -> bool:
        """Return True when this page has no children."""
        return not self.children


class DocumentTree:
    """A validated documentation hierarchy loaded from YAML."""

    def __init__(self, roots: list[DocumentNode]) -> None:
        """Create a tree from already-validated root nodes.

        Args:
            roots: Top-level pages in YAML order.
        """
        self._roots = roots

    @classmethod
    def from_yaml(cls, path: Path) -> DocumentTree:
        """Load and validate a YAML structure file.

        Args:
            path: Path to a YAML file whose root is a mapping.

        Returns:
            A validated document tree.

        Raises:
            DocumentTreeError: The file is missing, empty, or invalid.
        """
        if not path.is_file():
            raise DocumentTreeError(f"Structure file not found: {path}")
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise DocumentTreeError(
                f"Invalid YAML in {path}: {exc}"
            ) from exc
        if raw is None:
            raise DocumentTreeError(f"Structure file is empty: {path}")
        if not isinstance(raw, dict):
            raise DocumentTreeError(
                f"Structure root must be a mapping: {path}"
            )
        roots = cls._parse_mapping(raw, path=str(path))
        return cls(roots)

    @property
    def roots(self) -> list[DocumentNode]:
        """Return the top-level pages."""
        return self._roots

    def walk(self) -> list[DocumentNode]:
        """Return every page in depth-first order, parents first."""
        pages: list[DocumentNode] = []

        def visit(node: DocumentNode) -> None:
            pages.append(node)
            for child in node.children:
                visit(child)

        for root in self._roots:
            visit(root)
        return pages

    def page_count(self) -> int:
        """Return the number of pages in the tree."""
        return len(self.walk())

    def max_depth(self) -> int:
        """Return the deepest nesting level, counting roots as 1."""
        if not self._roots:
            return 0

        def depth(node: DocumentNode) -> int:
            if not node.children:
                return 1
            return 1 + max(depth(child) for child in node.children)

        return max(depth(root) for root in self._roots)

    def path_for(self, node: DocumentNode, output: Path) -> Path:
        """Return the directory path for a page under output.

        Args:
            node: Page whose directory is requested.
            output: Root output directory.

        Returns:
            Directory path for the page.
        """
        return output.joinpath(*self._path_parts(node))

    def _path_parts(self, node: DocumentNode) -> list[str]:
        """Return directory names from a root down to node."""
        for root in self._roots:
            parts = self._find_parts(root, node, [])
            if parts is not None:
                return parts
        raise DocumentTreeError(
            f"Page not found in tree: {node.title}"
        )

    def _find_parts(
        self,
        current: DocumentNode,
        target: DocumentNode,
        prefix: list[str],
    ) -> list[str] | None:
        path = [*prefix, current.directory]
        if current is target:
            return path
        for child in current.children:
            found = self._find_parts(child, target, path)
            if found is not None:
                return found
        return None

    @classmethod
    def _parse_mapping(
        cls,
        mapping: dict[Any, Any],
        *,
        path: str,
    ) -> list[DocumentNode]:
        nodes: list[DocumentNode] = []
        seen_dirs: set[str] = set()
        for key, value in mapping.items():
            if not isinstance(key, str) or not key.strip():
                raise DocumentTreeError(
                    f"Page title must be a non-empty string in {path}"
                )
            title = key.strip()
            node = cls._parse_node(title, value, path=f"{path}/{title}")
            if node.directory in seen_dirs:
                raise DocumentTreeError(
                    "Sibling pages share directory "
                    f"{node.directory!r} under {path}"
                )
            seen_dirs.add(node.directory)
            nodes.append(node)
        return nodes

    @classmethod
    def _parse_node(
        cls,
        title: str,
        value: Any,
        *,
        path: str,
    ) -> DocumentNode:
        directory = cls._directory_for_title(title, path)
        if isinstance(value, str):
            url = value.strip()
            if not url:
                raise DocumentTreeError(f"Missing URL for {path}")
            return DocumentNode(
                title=title,
                url=url,
                directory=directory,
            )
        if not isinstance(value, dict):
            raise DocumentTreeError(
                f"Page value must be a URL or mapping: {path}"
            )
        local = value.get("local") is True
        url: str | None = None
        if "url" in value:
            url_value = value["url"]
            if not isinstance(url_value, str) or not url_value.strip():
                raise DocumentTreeError(f"Invalid url for {path}")
            url = url_value.strip()
        elif not local:
            raise DocumentTreeError(f"Missing url for {path}")
        child_mapping = {
            key: child
            for key, child in value.items()
            if key not in {"url", "local"}
        }
        children = cls._parse_mapping(child_mapping, path=path)
        return DocumentNode(
            title=title,
            url=url,
            directory=directory,
            local=local,
            children=children,
        )

    @staticmethod
    def _directory_for_title(title: str, path: str) -> str:
        directory = slug_from_title(title)
        if not directory:
            raise DocumentTreeError(
                f"Title has no directory slug: {path}"
            )
        return directory

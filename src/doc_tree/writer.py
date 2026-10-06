"""Write documentation directories and index.md files."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from doc_tree.render import PageRenderer
from doc_tree.tree import DocumentNode, DocumentTree


class TreeWriterError(RuntimeError):
    """Raised when the tree cannot be written safely."""


@dataclass(frozen=True, slots=True)
class WritePlan:
    """Summary of what a write would produce."""

    page_count: int
    max_depth: int
    longest_path: Path
    paths: list[Path]


class TreeWriter:
    """Create directories and index.md files for a document tree."""

    def __init__(
        self,
        tree: DocumentTree,
        output: Path,
        renderer: PageRenderer | None = None,
        *,
        section_title: str | None = None,
        section_url: str | None = None,
        force: bool = False,
        progress: int = 0,
        stream=None,
    ) -> None:
        """Configure a writer for one output directory.

        Args:
            tree: Validated documentation tree.
            output: Directory that receives generated pages.
            renderer: Optional page renderer. Defaults to PageRenderer.
            section_title: Optional section page title.
            section_url: Optional section page URL.
            force: Replace existing index.md files when True.
            progress: Print progress every N pages. Zero disables.
            stream: Output stream for progress. Defaults to stdout.
        """
        if (section_title is None) != (section_url is None):
            raise TreeWriterError(
                "section-title and section-url must be used together"
            )
        self._tree = tree
        self._output = output
        self._renderer = renderer or PageRenderer()
        self._section_title = section_title
        self._section_url = section_url
        self._force = force
        self._progress = progress
        self._stream = stream if stream is not None else sys.stdout

    @property
    def has_section(self) -> bool:
        """Return True when a section index will be written."""
        return self._section_title is not None

    def plan(self) -> WritePlan:
        """Return the paths that would be written without writing."""
        paths: list[Path] = []
        if self.has_section:
            paths.append(self._output / "index.md")
        for node in self._tree.walk():
            paths.append(self._page_path(node) / "index.md")
        longest = max(paths, key=lambda path: len(str(path)))
        depth = self._tree.max_depth()
        if self.has_section:
            depth += 1
        return WritePlan(
            page_count=len(paths),
            max_depth=depth,
            longest_path=longest,
            paths=paths,
        )

    def write(self) -> WritePlan:
        """Create directories and index.md files.

        Returns:
            Summary of the paths written.

        Raises:
            TreeWriterError: An index.md exists and force is False.
        """
        write_plan = self.plan()
        for path in write_plan.paths:
            if path.exists() and not self._force:
                raise TreeWriterError(
                    f"Refusing to overwrite {path}; pass --force"
                )

        written = 0
        if self.has_section:
            assert self._section_title is not None
            assert self._section_url is not None
            text = self._renderer.render_section(
                self._section_title,
                self._section_url,
                self._tree.roots,
            )
            self._write_file(self._output / "index.md", text)
            written += 1
            self._maybe_progress(written, write_plan.page_count)

        for node in self._tree.walk():
            directory = self._page_path(node)
            text = self._renderer.render(node)
            self._write_file(directory / "index.md", text)
            written += 1
            self._maybe_progress(written, write_plan.page_count)

        return write_plan

    def _page_path(self, node: DocumentNode) -> Path:
        return self._tree.path_for(node, self._output)

    def _write_file(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _maybe_progress(self, written: int, total: int) -> None:
        if self._progress <= 0:
            return
        if written % self._progress == 0 or written == total:
            print(
                f"Wrote {written}/{total} pages",
                file=self._stream,
            )

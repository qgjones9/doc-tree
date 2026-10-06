"""Orchestrate scaffolding a documentation tree."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from doc_tree.nav import NavInserter, NavInserterError
from doc_tree.render import PageRenderer
from doc_tree.tree import DocumentTree, DocumentTreeError
from doc_tree.writer import TreeWriter, TreeWriterError


@dataclass(frozen=True, slots=True)
class ScaffoldOptions:
    """User options for one scaffold run."""

    structure: Path
    output: Path
    dry_run: bool = False
    force: bool = False
    progress: int = 0
    section_title: str | None = None
    section_url: str | None = None
    nav: Path | None = None
    nav_parent: str | None = None
    docs_prefix: str | None = None


class ScaffoldCommand:
    """Wire tree loading, writing, and optional nav insertion."""

    def __init__(
        self,
        options: ScaffoldOptions,
        *,
        renderer: PageRenderer | None = None,
    ) -> None:
        """Create a command for one set of options.

        Args:
            options: Paths and flags for the run.
            renderer: Optional page renderer override.
        """
        self._options = options
        self._renderer = renderer or PageRenderer()

    def run(self) -> int:
        """Execute the scaffold and return a process exit code.

        Returns:
            ``0`` on success, ``1`` on a handled error.
        """
        try:
            self._validate_options()
            tree = DocumentTree.from_yaml(self._options.structure)
            writer = TreeWriter(
                tree,
                self._options.output,
                self._renderer,
                section_title=self._options.section_title,
                section_url=self._options.section_url,
                force=self._options.force,
                progress=self._options.progress,
            )
            plan = writer.plan()
            print(f"Pages: {plan.page_count}")
            print(f"Max depth: {plan.max_depth}")
            print(f"Longest path: {plan.longest_path}")
            if self._options.dry_run:
                print("Dry run: no files written.")
                return 0
            writer.write()
            print(f"Wrote {plan.page_count} pages under "
                  f"{self._options.output}")
            if self._options.nav is not None:
                self._insert_nav(tree)
            return 0
        except (
            DocumentTreeError,
            TreeWriterError,
            NavInserterError,
            ValueError,
        ) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    def _validate_options(self) -> None:
        options = self._options
        if (options.section_title is None) != (
            options.section_url is None
        ):
            raise ValueError(
                "--section-title and --section-url must be used "
                "together"
            )
        if (options.nav is None) != (options.nav_parent is None):
            raise ValueError(
                "--nav and --nav-parent must be used together"
            )
        if options.nav is not None and options.docs_prefix is None:
            raise ValueError(
                "--docs-prefix is required when using --nav"
            )

    def _insert_nav(self, tree: DocumentTree) -> None:
        options = self._options
        assert options.nav is not None
        assert options.nav_parent is not None
        assert options.docs_prefix is not None
        inserter = NavInserter(
            tree,
            options.nav,
            options.nav_parent,
            docs_prefix=options.docs_prefix,
            section_title=options.section_title,
        )
        inserter.insert()
        print(f"Updated nav in {options.nav}")

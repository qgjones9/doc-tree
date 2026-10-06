"""Command-line interface for doc-tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from doc_tree import __version__
from doc_tree.scaffold import ScaffoldCommand, ScaffoldOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="doc-tree",
        description=(
            "Scaffold documentation directories from a "
            "title-and-URL YAML tree."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold = subparsers.add_parser(
        "scaffold",
        help="Create directories and index.md files from YAML.",
    )
    scaffold.add_argument(
        "--structure",
        type=Path,
        required=True,
        help="YAML file describing the documentation tree.",
    )
    scaffold.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory that receives the generated pages.",
    )
    scaffold.add_argument(
        "--section-title",
        help="Title for an optional section index page.",
    )
    scaffold.add_argument(
        "--section-url",
        help="URL for an optional section index page.",
    )
    scaffold.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the plan without writing files.",
    )
    scaffold.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing index.md files.",
    )
    scaffold.add_argument(
        "--progress",
        type=int,
        default=0,
        metavar="N",
        help="Print progress every N pages written.",
    )
    scaffold.add_argument(
        "--nav",
        type=Path,
        help="Optional MkDocs config file to update.",
    )
    scaffold.add_argument(
        "--nav-parent",
        help="Existing nav title that receives the tree.",
    )
    scaffold.add_argument(
        "--docs-prefix",
        help=(
            "Path prefix relative to the MkDocs docs_dir for "
            "generated pages. Required with --nav."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the selected command.

    Args:
        argv: Argument list without the program name. Defaults to
            ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scaffold":
        options = ScaffoldOptions(
            structure=args.structure,
            output=args.output,
            dry_run=args.dry_run,
            force=args.force,
            progress=args.progress,
            section_title=args.section_title,
            section_url=args.section_url,
            nav=args.nav,
            nav_parent=args.nav_parent,
            docs_prefix=args.docs_prefix,
        )
        return ScaffoldCommand(options).run()
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())

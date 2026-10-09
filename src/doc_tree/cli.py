"""Command-line interface for doc-tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from doc_tree import __version__
from doc_tree.apply import (
    MECHANICAL_OPS,
    ApplyError,
    apply_plan,
    load_plan,
    plan_file,
)
from doc_tree.plan import (
    build_plan,
    build_validate,
    default_structure_path,
    dump_plan,
    dump_validate,
    render_structure,
)
from doc_tree.scaffold import ScaffoldCommand, ScaffoldOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="doc-tree",
        description=(
            "Scaffold, validate, plan, and apply a title-and-URL "
            "documentation tree."
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
    validate = subparsers.add_parser(
        "validate",
        help="Report whether a documentation directory matches.",
    )
    validate.add_argument(
        "directory",
        type=Path,
        help="Documentation directory to read.",
    )
    _add_directory_command(
        subparsers,
        "plan",
        "Write a plan that normalizes a documentation directory.",
    )
    apply = _add_directory_command(
        subparsers,
        "apply",
        "Perform the ready actions in a plan file.",
    )
    apply.add_argument(
        "--op",
        action="append",
        dest="ops",
        metavar="OP",
        choices=sorted(MECHANICAL_OPS),
        help=(
            "Ready op to perform. Repeatable. Defaults to "
            "rename_directory, add_child_link, and "
            "remove_child_link."
        ),
    )
    apply.add_argument(
        "--skip",
        action="append",
        type=int,
        dest="skip",
        metavar="ID",
        help="Ready action id to leave unapplied. Repeatable.",
    )
    return parser


def _add_directory_command(
    subparsers: Any,
    name: str,
    help_text: str,
) -> Any:
    """Add a plan or apply subcommand.

    Args:
        subparsers: Parent subparser action.
        name: Subcommand name.
        help_text: One-line help.

    Returns:
        The created subparser.
    """
    command = subparsers.add_parser(name, help=help_text)
    command.add_argument(
        "directory",
        type=Path,
        help="Documentation directory to read.",
    )
    command.add_argument(
        "--plan",
        type=Path,
        help=(
            "Plan file path. Defaults to "
            "<directory>/<dirname>.plan.yaml."
        ),
    )
    return command


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
    if args.command == "validate":
        return _run_validate(args.directory)
    if args.command == "plan":
        return _run_plan(args.directory, args.plan)
    if args.command == "apply":
        return _run_apply(
            args.directory,
            args.plan,
            ops=set(args.ops) if args.ops else None,
            skip=set(args.skip) if args.skip else None,
        )
    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_validate(directory: Path) -> int:
    """Print a validate report without writing files.

    Args:
        directory: Documentation directory.

    Returns:
        ``0`` when the tree matches, ``1`` when actions remain
        or the directory cannot be read.
    """
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 1
    payload = build_validate(directory)
    print(dump_validate(payload), end="")
    return 0 if payload["ok"] else 1


def _run_plan(directory: Path, plan: Path | None) -> int:
    """Write a plan file and, when clean, the structure YAML.

    Args:
        directory: Documentation directory.
        plan: Optional plan path override.

    Returns:
        ``0`` when the tree matches, ``1`` when actions remain
        or the directory cannot be read.
    """
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 1
    destination = plan_file(directory, plan)
    payload = build_plan(directory)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(dump_plan(payload), encoding="utf-8")
    print(destination)
    if not payload["ok"]:
        return 1
    structure = default_structure_path(directory)
    structure.write_text(render_structure(directory), encoding="utf-8")
    return 0


def _run_apply(
    directory: Path,
    plan: Path | None,
    *,
    ops: set[str] | None,
    skip: set[int] | None,
) -> int:
    """Apply ready actions from a plan file.

    Args:
        directory: Documentation directory.
        plan: Optional plan path override.
        ops: Ops to perform, or None for the default set.
        skip: Ready action ids to leave unapplied.

    Returns:
        ``0`` on success, ``1`` when the plan cannot be applied.
    """
    if not directory.is_dir():
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 1
    try:
        payload = load_plan(plan_file(directory, plan))
        result = apply_plan(
            directory,
            payload,
            ops=ops,
            skip=skip,
        )
    except (ApplyError, OSError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"applied: {result['applied']}")
    print(f"left: {result['left']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

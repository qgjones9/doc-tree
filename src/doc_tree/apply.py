"""Apply ready actions from a documentation plan file."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from doc_tree.plan import default_plan_path

_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_BULLET = re.compile(r"^\s*[-*]\s+\[[^\]]+\]\([^)]+\)\s*$")

MECHANICAL_OPS = frozenset(
    {
        "rename_directory",
        "add_child_link",
        "remove_child_link",
    }
)


class ApplyError(RuntimeError):
    """Raised when a ready action cannot be performed."""


def load_plan(path: Path) -> dict[str, Any]:
    """Load a plan file.

    Args:
        path: Path to ``dirname.plan.yaml``.

    Returns:
        Parsed plan mapping.

    Raises:
        ApplyError: The file is missing or not a mapping.
    """
    if not path.is_file():
        raise ApplyError(f"Plan file not found: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ApplyError(f"Plan file is not a mapping: {path}")
    return loaded


def apply_plan(
    directory: Path,
    payload: dict[str, Any],
    *,
    ops: set[str] | None = None,
    skip: set[int] | None = None,
) -> dict[str, int]:
    """Perform selected ready actions in the order they are written.

    Args:
        directory: Documentation directory the plan describes.
        payload: Parsed plan mapping.
        ops: Ops to perform. Defaults to the mechanical set.
        skip: Ready action ids to leave unapplied.

    Returns:
        Mapping with ``applied`` and ``left`` counts. ``left`` is
        the number of ready actions that were not run.

    Raises:
        ApplyError: An action cannot be performed, or a filter is
            invalid.
    """
    selected = MECHANICAL_OPS if ops is None else frozenset(ops)
    unknown = selected - MECHANICAL_OPS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ApplyError(f"Unsupported apply op: {names}")
    skip_ids = set(skip or ())
    root = directory.resolve()
    moves: list[tuple[str, str]] = []
    actions = payload.get("actions") or []
    if not isinstance(actions, list):
        raise ApplyError("Plan actions must be a list")
    by_id = _ready_by_id(actions)
    for action_id in sorted(skip_ids):
        if action_id not in by_id:
            raise ApplyError(
                f"Skip id is missing or not ready: {action_id}"
            )
    applied = 0
    ready_count = 0
    for action in actions:
        if not isinstance(action, dict):
            raise ApplyError("Plan action must be a mapping")
        if action.get("status") != "ready":
            continue
        ready_count += 1
        action_id = action.get("id")
        if action_id in skip_ids:
            continue
        op = action.get("op")
        if op not in selected:
            continue
        if op == "rename_directory":
            _rename(root, action, moves)
        elif op == "add_child_link":
            _add_child_link(root, action, moves)
        elif op == "remove_child_link":
            _remove_child_link(root, action, moves)
        else:
            raise ApplyError(f"Unknown ready action: {op}")
        applied += 1
    return {"applied": applied, "left": ready_count - applied}


def _ready_by_id(actions: list[Any]) -> dict[int, dict[str, Any]]:
    found: dict[int, dict[str, Any]] = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("status") != "ready":
            continue
        action_id = action.get("id")
        if isinstance(action_id, int):
            found[action_id] = action
    return found


def _rename(
    root: Path,
    action: dict[str, Any],
    moves: list[tuple[str, str]],
) -> None:
    original = str(action["from"])
    current = _map_rel(original, moves)
    source = _at(root, current)
    if not source.is_dir():
        raise ApplyError(f"Missing directory: {current}")
    destination = source.parent / str(action["to"])
    if destination.exists():
        raise ApplyError(f"Destination exists: {destination.name}")
    old_abs = Path(os.path.normpath(source))
    source.rename(destination)
    moves.append((original, _renamed_rel(original, str(action["to"]))))
    new_abs = Path(os.path.normpath(destination))
    for link in action.get("links") or []:
        _rewrite_link(root, str(link), moves, old_abs, new_abs)


def _renamed_rel(rel: str, new_name: str) -> str:
    parent = Path(rel).parent.as_posix()
    if parent in {".", ""}:
        return new_name
    return f"{parent}/{new_name}"


def _rewrite_link(
    root: Path,
    link: str,
    moves: list[tuple[str, str]],
    old_abs: Path,
    new_abs: Path,
) -> None:
    current = _at(root, _map_rel(link, moves))
    if current.name in {"mkdocs.yml", "mkdocs.yaml"}:
        _rewrite_mkdocs(current, old_abs, new_abs)
        return
    if not current.is_file():
        raise ApplyError(f"Missing link file: {link}")
    text = current.read_text(encoding="utf-8")
    original_file = _at(root, link)

    def replace(match: re.Match[str]) -> str:
        href = match.group(2).strip()
        if "://" in href:
            return match.group(0)
        raw, suffix = _split_suffix(href)
        if not raw:
            return match.group(0)
        resolved = Path(os.path.normpath(original_file.parent / raw))
        if resolved != old_abs and resolved != old_abs / "index.md":
            return match.group(0)
        target = new_abs / "index.md"
        if not raw.endswith("index.md") and resolved == old_abs:
            target = new_abs
        relative = Path(
            os.path.relpath(target, current.parent)
        ).as_posix()
        return f"[{match.group(1)}]({relative}{suffix})"

    current.write_text(_LINK.sub(replace, text), encoding="utf-8")


def _rewrite_mkdocs(path: Path, old_abs: Path, new_abs: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in zip(
        _docs_nav_paths(old_abs),
        _docs_nav_paths(new_abs),
        strict=True,
    ):
        text = _replace_path(text, old, new)
    path.write_text(text, encoding="utf-8")


def _replace_path(text: str, old: str, new: str) -> str:
    pattern = re.compile(
        r"(?<![\w.-])" + re.escape(old) + r"(?![\w.-])"
    )
    return pattern.sub(new, text)


def _docs_nav_paths(path: Path) -> list[str]:
    """Return MkDocs nav path forms for a page under docs/.

    Nav entries are usually relative to ``docs_dir`` (no ``docs/``
    prefix). Also include the ``docs/...`` form for configs that
    store that.
    """
    for parent in [path, *path.parents]:
        if parent.name == "docs":
            rel = path.relative_to(parent).as_posix()
            return [rel, f"docs/{rel}"]
    return []


def _add_child_link(
    root: Path,
    action: dict[str, Any],
    moves: list[tuple[str, str]],
) -> None:
    path = _at(root, _map_rel(str(action["index"]), moves))
    text = path.read_text(encoding="utf-8")
    line = f"- [{action['title']}]({action['href']})\n"
    if f"]({action['href']})" in text:
        return
    path.write_text(_insert_child_link(text, line), encoding="utf-8")


_CHILD_PAGES_HEADING = "## Child pages"


def _insert_child_link(text: str, line: str) -> str:
    lines = text.splitlines(keepends=True)
    heading = _find_child_pages_heading(lines)
    if heading is None:
        return _append_child_pages_section(text, line)
    last_bullet = _last_bullet_in_section(lines, heading)
    if last_bullet is not None:
        lines.insert(last_bullet + 1, line)
        return "".join(lines)
    insert_at = heading + 1
    block = ["\n", line]
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        block = [line]
        insert_at += 1
    lines[insert_at:insert_at] = block
    return "".join(lines)


def _find_child_pages_heading(lines: list[str]) -> int | None:
    for index, existing in enumerate(lines):
        if existing.rstrip("\n") == _CHILD_PAGES_HEADING:
            return index
    return None


def _last_bullet_in_section(
    lines: list[str],
    heading: int,
) -> int | None:
    last_bullet = None
    for index in range(heading + 1, len(lines)):
        stripped = lines[index].lstrip()
        if stripped.startswith("## ") or stripped.startswith("##\t"):
            break
        if _BULLET.match(lines[index].rstrip("\n")):
            last_bullet = index
    return last_bullet


def _append_child_pages_section(text: str, line: str) -> str:
    body = text
    if body and not body.endswith("\n"):
        body += "\n"
    if body and not body.endswith("\n\n"):
        body += "\n"
    return f"{body}{_CHILD_PAGES_HEADING}\n\n{line}"


def _remove_child_link(
    root: Path,
    action: dict[str, Any],
    moves: list[tuple[str, str]],
) -> None:
    path = _at(root, _map_rel(str(action["index"]), moves))
    href = str(action["href"])
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        if _BULLET.match(line.rstrip("\n")) and f"]({href})" in line:
            continue
        kept.append(line)
    path.write_text("".join(kept), encoding="utf-8")


def _split_suffix(href: str) -> tuple[str, str]:
    if "#" in href:
        raw, fragment = href.split("#", 1)
        return raw.strip(), "#" + fragment
    return href.strip(), ""


def _map_rel(rel: str, moves: list[tuple[str, str]]) -> str:
    current = rel
    for old, new in moves:
        if current == old or current.startswith(old + "/"):
            current = new + current[len(old) :]
    return current


def _at(root: Path, rel: str) -> Path:
    if rel in {"", "."}:
        return root
    return root.joinpath(*Path(rel).parts)


def plan_file(directory: Path, override: Path | None) -> Path:
    """Return the plan path, honoring an explicit override.

    Args:
        directory: Documentation directory.
        override: ``--plan`` path, when set.

    Returns:
        Plan file path.
    """
    if override is not None:
        return override
    return default_plan_path(directory)

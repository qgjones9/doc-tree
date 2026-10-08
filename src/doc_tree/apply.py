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


def apply_plan(directory: Path, payload: dict[str, Any]) -> None:
    """Perform ready actions in the order they are written.

    Args:
        directory: Documentation directory the plan describes.
        payload: Parsed plan mapping.

    Raises:
        ApplyError: An action cannot be performed.
    """
    root = directory.resolve()
    moves: list[tuple[str, str]] = []
    actions = payload.get("actions") or []
    if not isinstance(actions, list):
        raise ApplyError("Plan actions must be a list")
    for action in actions:
        if not isinstance(action, dict):
            raise ApplyError("Plan action must be a mapping")
        if action.get("status") != "ready":
            continue
        op = action.get("op")
        if op == "rename_directory":
            _rename(root, action, moves)
        elif op == "add_child_link":
            _add_child_link(root, action, moves)
        elif op == "remove_child_link":
            _remove_child_link(root, action, moves)
        elif op == "set_h1_link":
            _set_h1_link(root, action, moves)
        else:
            raise ApplyError(f"Unknown ready action: {op}")


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
    old_docs = _docs_rel(old_abs)
    new_docs = _docs_rel(new_abs)
    if old_docs and new_docs:
        text = _replace_path(text, old_docs, new_docs)
    path.write_text(text, encoding="utf-8")


def _replace_path(text: str, old: str, new: str) -> str:
    pattern = re.compile(
        r"(?<![\w.-])" + re.escape(old) + r"(?![\w.-])"
    )
    return pattern.sub(new, text)


def _docs_rel(path: Path) -> str | None:
    for parent in [path, *path.parents]:
        if parent.name == "docs":
            return Path("docs", path.relative_to(parent)).as_posix()
    return None


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


def _insert_child_link(text: str, line: str) -> str:
    lines = text.splitlines(keepends=True)
    last_bullet = None
    for index, existing in enumerate(lines):
        if _BULLET.match(existing.rstrip("\n")):
            last_bullet = index
    if last_bullet is not None:
        lines.insert(last_bullet + 1, line)
        return "".join(lines)
    for index, existing in enumerate(lines):
        stripped = existing.lstrip()
        if stripped.startswith("# ") or stripped.startswith("#\t"):
            block = ["\n", line]
            lines[index + 1 : index + 1] = block
            return "".join(lines)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + line


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


def _set_h1_link(
    root: Path,
    action: dict[str, Any],
    moves: list[tuple[str, str]],
) -> None:
    path = _at(root, _map_rel(str(action["index"]), moves))
    title = str(action["title"])
    url = str(action["url"])
    pattern = re.compile(
        r"^#\s+" + re.escape(title) + r"\s*$",
        re.MULTILINE,
    )
    replacement = f"# [{title}]({url})"
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ApplyError(f"H1 not found in {action['index']}")
    path.write_text(updated, encoding="utf-8")


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

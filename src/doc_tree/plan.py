"""Compare a documentation directory with the title-slug tree."""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from doc_tree.page import ParsedPage, parse_page
from doc_tree.tree import slug_from_title

_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_KEY_SPECIAL = re.compile(r"""[:#\[\]\{\},&*!|>%@`'"\\]""")


@dataclass(frozen=True, slots=True)
class _Page:
    rel_dir: str
    index_rel: str
    directory: Path
    parsed: ParsedPage | None


def default_plan_path(directory: Path) -> Path:
    """Return the plan file path for a documentation directory.

    Args:
        directory: Directory passed to ``plan``.

    Returns:
        ``<directory>/<dirname>.plan.yaml``.
    """
    return directory / f"{directory.name}.plan.yaml"


def default_structure_path(directory: Path) -> Path:
    """Return the structure YAML path for a documentation directory.

    Args:
        directory: Directory passed to ``plan``.

    Returns:
        ``<directory>/<dirname>.yaml``.
    """
    return directory / f"{directory.name}.yaml"


def inspect_tree(directory: Path) -> list[dict[str, Any]]:
    """Classify a documentation directory without scanning rename links.

    Args:
        directory: Existing documentation directory.

    Returns:
        Ordered actions, ready deepest first, then blocked. Ids are
        not assigned.
    """
    root = directory.resolve()
    pages = _collect(root)
    return _ordered_actions(_actions(root, pages))


def build_plan(directory: Path) -> dict[str, Any]:
    """Build the plan payload for a documentation directory.

    Args:
        directory: Existing documentation directory.

    Returns:
        Mapping with ``ok``, ``directory``, and ``actions``.
    """
    root = directory.resolve()
    pages = _collect(root)
    actions = _ordered_actions(_actions(root, pages))
    _attach_rename_links(root, actions)
    numbered = [
        _with_id(number, action)
        for number, action in enumerate(actions, start=1)
    ]
    return {
        "ok": not numbered,
        "directory": directory.name,
        "actions": numbered,
    }


def build_validate(directory: Path) -> dict[str, Any]:
    """Build the validate report for a documentation directory.

    Args:
        directory: Existing documentation directory.

    Returns:
        Mapping with ``ok``, ``directory``, action counts, and
        blocked rows. Ready actions are counts only.
    """
    actions = inspect_tree(directory)
    counts = Counter(str(action["op"]) for action in actions)
    blocked = [
        action for action in actions if action.get("status") != "ready"
    ]
    return {
        "ok": not actions,
        "directory": directory.name,
        "actions": dict(sorted(counts.items())),
        "blocked": blocked,
    }


def render_structure(directory: Path) -> str:
    """Render the structure YAML for a directory that already matches.

    Args:
        directory: Documentation directory whose plan has no actions.

    Returns:
        YAML text. The section page itself is not a key.
    """
    nodes = _structure_nodes(directory.resolve())
    lines = _emit_nodes(nodes, 0)
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def dump_plan(payload: dict[str, Any]) -> str:
    """Serialize a plan payload.

    Args:
        payload: Plan mapping from :func:`build_plan`.

    Returns:
        YAML text.
    """
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
    )


def dump_validate(payload: dict[str, Any]) -> str:
    """Serialize a validate report.

    Args:
        payload: Report mapping from :func:`build_validate`.

    Returns:
        YAML text.
    """
    return yaml.safe_dump(
        payload,
        sort_keys=False,
        allow_unicode=True,
    )


def _collect(root: Path) -> list[_Page]:
    pages: list[_Page] = []

    def visit(directory: Path) -> None:
        rel = _rel(directory, root)
        index_rel = f"{rel}/index.md" if rel else "index.md"
        index = directory / "index.md"
        parsed = None
        if index.is_file():
            parsed = parse_page(index.read_text(encoding="utf-8"))
        pages.append(
            _Page(
                rel_dir=rel,
                index_rel=index_rel,
                directory=directory,
                parsed=parsed,
            )
        )
        for child in _child_dirs(directory):
            visit(child)

    visit(root)
    return pages


def _actions(root: Path, pages: list[_Page]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    by_rel = {page.rel_dir: page for page in pages}
    collisions = _collisions(root, pages)
    colliding = {
        page.rel_dir
        for group in collisions.values()
        for page in group
    }
    for page in pages:
        if page.parsed is None:
            actions.append(
                {
                    "status": "blocked",
                    "op": "create_index",
                    "path": page.rel_dir or ".",
                }
            )
            continue
        actions.extend(_page_actions(page, by_rel, colliding))
    for path, group in collisions.items():
        actions.append(
            {
                "status": "blocked",
                "op": "slug_collision",
                "path": path,
                "siblings": [page.index_rel for page in group],
            }
        )
    return actions


def _ordered_actions(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ready = [item for item in actions if item["status"] == "ready"]
    blocked = [item for item in actions if item["status"] != "ready"]
    ready.sort(key=lambda action: (-_depth(action), _action_path(action)))
    return [*ready, *blocked]


def _attach_rename_links(
    root: Path,
    actions: list[dict[str, Any]],
) -> None:
    renames = [
        action
        for action in actions
        if action.get("op") == "rename_directory"
    ]
    if not renames:
        return
    by_dir: dict[Path, dict[str, Any]] = {}
    resolve_to_dir: dict[Path, Path] = {}
    found: dict[Path, set[str]] = {}
    for action in renames:
        target = (root / str(action["from"])).resolve()
        by_dir[target] = action
        resolve_to_dir[target] = target
        resolve_to_dir[target / "index.md"] = target
        found[target] = set()
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            name for name in dirnames if not name.startswith(".")
        )
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            path = Path(directory) / name
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(root).as_posix()
            for matched in _markdown_link_targets(path, text):
                target = resolve_to_dir.get(matched)
                if target is not None:
                    found[target].add(rel)
    mkdocs = _find_mkdocs(root)
    mkdocs_text = None
    mkdocs_rel = None
    if mkdocs is not None:
        mkdocs_text = mkdocs.read_text(encoding="utf-8")
        mkdocs_rel = Path(os.path.relpath(mkdocs, root)).as_posix()
    for target, action in by_dir.items():
        links = found[target]
        if mkdocs_text is not None and mkdocs_rel is not None:
            if _mkdocs_mentions_text(mkdocs_text, root, target):
                links.add(mkdocs_rel)
        action["links"] = sorted(links)


def _page_actions(
    page: _Page,
    by_rel: dict[str, _Page],
    colliding: set[str],
) -> list[dict[str, Any]]:
    parsed = page.parsed
    assert parsed is not None
    actions: list[dict[str, Any]] = []
    if not parsed.title or not slug_from_title(parsed.title):
        actions.append(_need_url(page))
        return actions
    if _needs_set_h1_link(parsed):
        actions.append(
            {
                "status": "blocked",
                "op": "set_h1_link",
                "index": page.index_rel,
                "title": parsed.title,
                "url": parsed.embedded_url,
            }
        )
        return actions
    if parsed.plain_h1 and not parsed.local:
        actions.append(_need_url(page))
    slug = slug_from_title(parsed.title)
    if (
        page.rel_dir
        and page.rel_dir not in colliding
        and Path(page.rel_dir).name != slug
    ):
        actions.append(
            {
                "status": "ready",
                "op": "rename_directory",
                "from": page.rel_dir,
                "to": slug,
                "h1": parsed.title,
            }
        )
    actions.extend(_child_link_actions(page, by_rel, colliding))
    return actions


def _needs_set_h1_link(parsed: ParsedPage) -> bool:
    return bool(
        parsed.plain_h1 and not parsed.local and parsed.embedded_url
    )


def _child_link_actions(
    page: _Page,
    by_rel: dict[str, _Page],
    colliding: set[str],
) -> list[dict[str, Any]]:
    parsed = page.parsed
    assert parsed is not None
    listed = {link.directory: link for link in parsed.child_links}
    actual = {
        child.name: _child_rel(page.rel_dir, child.name)
        for child in _child_dirs(page.directory)
    }
    actions: list[dict[str, Any]] = []
    for name, rel in sorted(actual.items()):
        if name in listed:
            continue
        child = by_rel.get(rel)
        if (
            child is None
            or child.parsed is None
            or not child.parsed.title
            or rel in colliding
            or _needs_set_h1_link(child.parsed)
        ):
            continue
        slug = slug_from_title(child.parsed.title)
        if not slug:
            continue
        actions.append(
            {
                "status": "ready",
                "op": "add_child_link",
                "index": page.index_rel,
                "title": child.parsed.title,
                "href": f"{slug}/index.md",
            }
        )
    for name, link in listed.items():
        if name in actual:
            continue
        actions.append(
            {
                "status": "ready",
                "op": "remove_child_link",
                "index": page.index_rel,
                "title": link.title,
                "href": link.href,
            }
        )
    return actions


def _collisions(
    root: Path,
    pages: list[_Page],
) -> dict[str, list[_Page]]:
    groups: dict[tuple[str, str], list[_Page]] = {}
    for page in pages:
        if not page.rel_dir or page.parsed is None or not page.parsed.title:
            continue
        slug = slug_from_title(page.parsed.title)
        if not slug:
            continue
        parent = str(Path(page.rel_dir).parent.as_posix())
        if parent == ".":
            parent = ""
        groups.setdefault((parent, slug), []).append(page)
    base = _path_base(root)
    found: dict[str, list[_Page]] = {}
    for (parent, slug), group in groups.items():
        if len(group) < 2:
            continue
        parent_dir = root if not parent else root / parent
        target = parent_dir / slug
        found[_display_path(target, base)] = group
    return found


def _markdown_link_targets(path: Path, text: str) -> set[Path]:
    targets: set[Path] = set()
    for match in _LINK.finditer(text):
        href = match.group(1).strip()
        if "://" in href:
            continue
        raw = href.split("#", 1)[0].split("?", 1)[0].strip()
        if not raw:
            continue
        targets.add(Path(os.path.normpath(path.parent / raw)))
    return targets


def _mkdocs_mentions_text(
    text: str,
    root: Path,
    target: Path,
) -> bool:
    rel = target.resolve().relative_to(root).as_posix()
    candidates = [rel, *_docs_nav_paths(target.resolve())]
    for candidate in candidates:
        if candidate and _contains_path(text, candidate):
            return True
    return False


def _contains_path(text: str, path: str) -> bool:
    pattern = re.compile(
        r"(?<![\w.-])" + re.escape(path) + r"(?![\w.-])"
    )
    return pattern.search(text) is not None


def _find_mkdocs(root: Path) -> Path | None:
    current = root.resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "mkdocs.yml"
        if candidate.is_file():
            return candidate
        if parent.name == "docs":
            above = parent.parent / "mkdocs.yml"
            if above.is_file():
                return above
            return None
    return None


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


def _path_base(root: Path) -> Path:
    current = root.resolve()
    for parent in [current, *current.parents]:
        if parent.name == "docs":
            return parent
    return current


def _display_path(target: Path, base: Path) -> str:
    target = target.resolve()
    base = base.resolve()
    if base.name == "docs":
        return Path("docs", target.relative_to(base)).as_posix()
    return target.relative_to(base).as_posix()


def _structure_nodes(directory: Path) -> list[dict[str, Any]]:
    index = directory / "index.md"
    parsed = parse_page(index.read_text(encoding="utf-8"))
    nodes: list[dict[str, Any]] = []
    for link in parsed.child_links:
        child = directory / link.directory
        child_parsed = parse_page(
            (child / "index.md").read_text(encoding="utf-8")
        )
        assert child_parsed.title is not None
        nodes.append(
            {
                "title": child_parsed.title,
                "url": child_parsed.url,
                "local": child_parsed.local,
                "children": _structure_nodes(child),
            }
        )
    return nodes


def _emit_nodes(nodes: list[dict[str, Any]], indent: int) -> list[str]:
    lines: list[str] = []
    pad = "  " * indent
    inner = "  " * (indent + 1)
    for node in nodes:
        key = _quote_key(str(node["title"]))
        children = node["children"]
        local = bool(node["local"])
        url = node["url"]
        if not children and not local and url:
            lines.append(f"{pad}{key}: {url}")
            continue
        lines.append(f"{pad}{key}:")
        if local:
            lines.append(f"{inner}local: true")
        if url:
            lines.append(f"{inner}url: {url}")
        lines.extend(_emit_nodes(children, indent + 1))
    return lines


def _quote_key(title: str) -> str:
    if _KEY_SPECIAL.search(title) or title != title.strip():
        escaped = title.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return title


def _need_url(page: _Page) -> dict[str, str]:
    return {
        "status": "blocked",
        "op": "need_source_url",
        "index": page.index_rel,
    }


def _depth(action: dict[str, Any]) -> int:
    raw = _action_path(action)
    if raw in {"", "."}:
        return 0
    return len(Path(raw).parts)


def _action_path(action: dict[str, Any]) -> str:
    return str(
        action.get("from")
        or action.get("index")
        or action.get("path")
        or ""
    )


def _with_id(number: int, action: dict[str, Any]) -> dict[str, Any]:
    preferred = (
        "id",
        "status",
        "op",
        "from",
        "to",
        "h1",
        "path",
        "index",
        "title",
        "url",
        "href",
        "links",
        "siblings",
    )
    merged: dict[str, Any] = {"id": number, **action}
    ordered: dict[str, Any] = {}
    for key in preferred:
        if key in merged:
            ordered[key] = merged[key]
    for key, value in merged.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _child_dirs(directory: Path) -> list[Path]:
    return sorted(
        (
            entry
            for entry in directory.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ),
        key=lambda entry: entry.name,
    )


def _child_rel(parent: str, name: str) -> str:
    if not parent:
        return name
    return f"{parent}/{name}"


def _rel(directory: Path, root: Path) -> str:
    relative = directory.resolve().relative_to(root.resolve())
    text = relative.as_posix()
    return "" if text == "." else text

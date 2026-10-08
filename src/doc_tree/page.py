"""Parse an index.md page without changing its prose."""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml


_H1_LINK = re.compile(r"^#\s+\[([^\]]+)\]\(([^)]+)\)\s*$")
_H1_PLAIN = re.compile(r"^#\s+(.+?)\s*$")
_BULLET_LINK = re.compile(
    r"^\s*[-*]\s+\[([^\]]+)\]\(([^)]+)\)\s*$"
)
_URL = re.compile(r"https?://[^\s)>\"]+")


@dataclass(frozen=True, slots=True)
class ChildLink:
    """One direct-child link in a parent index."""

    title: str
    href: str
    directory: str


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """The heading and child list read from an index.md file."""

    title: str | None
    url: str | None
    local: bool
    plain_h1: bool
    embedded_url: str | None
    child_links: tuple[ChildLink, ...]


def parse_page(text: str) -> ParsedPage:
    """Read the H1, optional local flag, and direct child links.

    Args:
        text: Full index.md text.

    Returns:
        Parsed heading and child links. Prose is not returned.
    """
    frontmatter, body = _split_frontmatter(text)
    local = frontmatter.get("local") is True
    embedded = _embedded_url(frontmatter, text)
    title: str | None = None
    url: str | None = None
    plain_h1 = False
    for line in body.splitlines():
        if not line.startswith("# ") and not line.startswith("#\t"):
            continue
        linked = _H1_LINK.match(line.strip())
        if linked:
            title = linked.group(1).strip()
            url = linked.group(2).strip()
            break
        plain = _H1_PLAIN.match(line.strip())
        if plain and not plain.group(1).startswith("#"):
            title = plain.group(1).strip()
            plain_h1 = True
            break
    children: list[ChildLink] = []
    for line in body.splitlines():
        match = _BULLET_LINK.match(line)
        if not match:
            continue
        directory = direct_child_directory(match.group(2).strip())
        if directory is None:
            continue
        children.append(
            ChildLink(
                title=match.group(1).strip(),
                href=match.group(2).strip(),
                directory=directory,
            )
        )
    return ParsedPage(
        title=title,
        url=url,
        local=local,
        plain_h1=plain_h1,
        embedded_url=embedded,
        child_links=tuple(children),
    )


def direct_child_directory(href: str) -> str | None:
    """Return the child directory name when href points at one.

    Args:
        href: Markdown link target.

    Returns:
        Directory name, or None when the link is not a direct child.
    """
    raw = href.split("#", 1)[0].split("?", 1)[0].strip()
    if not raw or "://" in raw:
        return None
    if raw.startswith("./"):
        raw = raw[2:]
    if raw.endswith("/index.md"):
        name = raw[: -len("/index.md")]
    elif raw.endswith("/"):
        name = raw[:-1]
    else:
        return None
    if not name or "/" in name or name in {".", ".."}:
        return None
    return name


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    loaded = yaml.safe_load(text[4:end])
    body = text[end + 5 :]
    if not isinstance(loaded, dict):
        return {}, body
    return loaded, body


def _embedded_url(
    frontmatter: dict[str, object],
    text: str,
) -> str | None:
    raw = frontmatter.get("url")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    match = _URL.search(text)
    if match is None:
        return None
    return match.group(0).rstrip(".,")

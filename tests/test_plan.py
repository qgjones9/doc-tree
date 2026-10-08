"""Tests for doc-tree plan and apply."""

from __future__ import annotations

from pathlib import Path

import yaml

from doc_tree.cli import main


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def linked(title: str, url: str, children: list[tuple[str, str]]) -> str:
    lines = [f"# [{title}]({url})\n"]
    if children:
        lines.append("\n")
        for child_title, directory in children:
            lines.append(f"- [{child_title}]({directory}/index.md)\n")
    return "".join(lines)


def test_matching_tree_writes_structure(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Models", "models")],
        ),
    )
    write(
        root / "models" / "index.md",
        linked(
            "Models",
            "https://example.com/models",
            [("Alpha", "alpha")],
        ),
    )
    write(
        root / "models" / "alpha" / "index.md",
        linked(
            "Alpha",
            "https://example.com/alpha",
            [("Alpha One", "alpha-one")],
        ),
    )
    write(
        root / "models" / "alpha" / "alpha-one" / "index.md",
        linked("Alpha One", "https://example.com/alpha-one", []),
    )
    code = main(["plan", str(root)])
    assert code == 0
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    assert plan["ok"] is True
    assert plan["actions"] == []
    structure = (root / "guide.yaml").read_text(encoding="utf-8")
    assert "Alpha One: https://example.com/alpha-one" in structure
    assert "Guide:" not in structure


def test_url_without_filename_still_matches(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Overview", "overview")],
        ),
    )
    write(
        root / "overview" / "index.md",
        linked("Overview", "https://example.com/docs/", []),
    )
    assert main(["plan", str(root)]) == 0
    text = (root / "guide.yaml").read_text(encoding="utf-8")
    assert "Overview: https://example.com/docs/" in text


def test_local_page_omits_url(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("A note I wrote", "a-note-i-wrote")],
        ),
    )
    write(
        root / "a-note-i-wrote" / "index.md",
        "---\nlocal: true\n---\n# A note I wrote\n",
    )
    assert main(["plan", str(root)]) == 0
    text = (root / "guide.yaml").read_text(encoding="utf-8")
    assert "local: true" in text
    assert "url:" not in text


def test_plain_h1_needs_source_url(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Plain title", "plain-title")],
        ),
    )
    write(root / "plain-title" / "index.md", "# Plain title\n")
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    assert plan["ok"] is False
    assert any(
        action["op"] == "need_source_url" for action in plan["actions"]
    )
    assert not (root / "guide.yaml").exists()


def test_same_slug_under_different_parents(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Models", "models"), ("Build", "build")],
        ),
    )
    for parent in ("models", "build"):
        write(
            root / parent / "index.md",
            linked(
                parent.title(),
                f"https://example.com/{parent}",
                [("Overview", "overview")],
            ),
        )
        write(
            root / parent / "overview" / "index.md",
            linked("Overview", f"https://example.com/{parent}/overview", []),
        )
    assert main(["plan", str(root)]) == 0


def test_docs_path_collision_is_blocked(tmp_path: Path) -> None:
    root = tmp_path / "docs" / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [
                ("Overview", "overview-a"),
                ("Overview", "overview-b"),
            ],
        ),
    )
    for name in ("overview-a", "overview-b"):
        write(
            root / name / "index.md",
            linked("Overview", f"https://example.com/{name}", []),
        )
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    collisions = [
        action
        for action in plan["actions"]
        if action["op"] == "slug_collision"
    ]
    assert len(collisions) == 1
    assert collisions[0]["status"] == "blocked"
    assert collisions[0]["path"] == "docs/guide/overview"
    assert collisions[0]["siblings"] == [
        "overview-a/index.md",
        "overview-b/index.md",
    ]
    assert not any(
        action["op"] == "rename_directory" for action in plan["actions"]
    )


def test_ready_renames_are_deepest_first(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Wrong Parent", "wrong-parent")],
        ),
    )
    write(
        root / "wrong-parent" / "index.md",
        linked(
            "Parent",
            "https://example.com/parent",
            [("Wrong Child", "wrong-child")],
        ),
    )
    write(
        root / "wrong-parent" / "wrong-child" / "index.md",
        linked("Child", "https://example.com/child", []),
    )
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    renames = [
        action["from"]
        for action in plan["actions"]
        if action["op"] == "rename_directory"
    ]
    assert renames == [
        "wrong-parent/wrong-child",
        "wrong-parent",
    ]


def test_apply_rewrites_listed_links_and_skips_blocked(
    tmp_path: Path,
) -> None:
    root = tmp_path / "user-guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [
                ("Models at a glance", "old-name"),
                ("Blocked", "blocked"),
                ("Other", "other"),
            ],
        ),
    )
    write(
        root / "old-name" / "index.md",
        linked(
            "Models at a glance",
            "https://example.com/models",
            [],
        ),
    )
    blocked = root / "blocked" / "index.md"
    write(blocked, "# Blocked\n")
    write(
        root / "other" / "index.md",
        linked("Other", "https://example.com/other", [])
        + "\nSee [models](../old-name/index.md).\n",
    )
    blocked_text = blocked.read_text(encoding="utf-8")
    assert main(["plan", str(root)]) == 1
    plan_path = root / "user-guide.plan.yaml"
    plan_text = plan_path.read_text(encoding="utf-8")
    plan = yaml.safe_load(plan_text)
    rename = next(
        action
        for action in plan["actions"]
        if action["op"] == "rename_directory"
    )
    assert "index.md" in rename["links"]
    assert "other/index.md" in rename["links"]
    assert main(["apply", str(root)]) == 0
    assert plan_path.read_text(encoding="utf-8") == plan_text
    assert blocked.read_text(encoding="utf-8") == blocked_text
    assert not (root / "old-name").exists()
    assert (root / "models-at-a-glance" / "index.md").is_file()
    parent = (root / "index.md").read_text(encoding="utf-8")
    assert "(models-at-a-glance/index.md)" in parent
    assert "(old-name/index.md)" not in parent
    other = (root / "other" / "index.md").read_text(encoding="utf-8")
    assert "(../models-at-a-glance/index.md)" in other
    assert "old-name" not in other


def test_apply_renames_deepest_directory_first(tmp_path: Path) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Wrong Parent", "wrong-parent")],
        ),
    )
    write(
        root / "wrong-parent" / "index.md",
        linked(
            "Parent",
            "https://example.com/parent",
            [("Wrong Child", "wrong-child")],
        ),
    )
    write(
        root / "wrong-parent" / "wrong-child" / "index.md",
        linked("Child", "https://example.com/child", []),
    )
    assert main(["plan", str(root)]) == 1
    assert main(["apply", str(root)]) == 0
    assert (root / "parent" / "child" / "index.md").is_file()
    parent = (root / "parent" / "index.md").read_text(encoding="utf-8")
    assert "(child/index.md)" in parent
    section = (root / "index.md").read_text(encoding="utf-8")
    assert "(parent/index.md)" in section

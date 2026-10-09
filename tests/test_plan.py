"""Tests for doc-tree plan, validate, and apply."""

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


def test_validate_matching_tree_writes_nothing(
    tmp_path: Path,
    capsys,
) -> None:
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
        linked("Overview", "https://example.com/overview", []),
    )
    code = main(["validate", str(root)])
    captured = capsys.readouterr()
    report = yaml.safe_load(captured.out)
    assert code == 0
    assert report["ok"] is True
    assert report["actions"] == {}
    assert report["blocked"] == []
    assert not (root / "guide.plan.yaml").exists()
    assert not (root / "guide.yaml").exists()


def test_validate_rename_only_skips_links(
    tmp_path: Path,
    capsys,
) -> None:
    root = tmp_path / "guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Wrong Name", "wrong-name")],
        ),
    )
    write(
        root / "wrong-name" / "index.md",
        linked("Models", "https://example.com/models", []),
    )
    code = main(["validate", str(root)])
    captured = capsys.readouterr()
    report = yaml.safe_load(captured.out)
    assert code == 1
    assert report["ok"] is False
    assert report["actions"]["rename_directory"] == 1
    assert "links" not in captured.out
    assert report["blocked"] == []
    assert not (root / "guide.plan.yaml").exists()


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


def test_set_h1_link_is_blocked_and_skips_rename(
    tmp_path: Path,
) -> None:
    root = tmp_path / "guide"
    heading = (
        "# [[Example] Create a rule]("
        "https://example.com/rule.md)\n"
    )
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Old Folder", "old-folder")],
        ),
    )
    write(root / "old-folder" / "index.md", heading)
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    blocked = [
        action
        for action in plan["actions"]
        if action["op"] == "set_h1_link"
    ]
    assert len(blocked) == 1
    assert blocked[0]["status"] == "blocked"
    assert not any(
        action["op"] == "rename_directory" for action in plan["actions"]
    )
    plan_text = (root / "guide.plan.yaml").read_text(encoding="utf-8")
    assert main(["apply", str(root)]) == 0
    assert (root / "old-folder" / "index.md").read_text(
        encoding="utf-8"
    ) == heading
    assert (root / "guide.plan.yaml").read_text(
        encoding="utf-8"
    ) == plan_text


def test_apply_rewrites_mkdocs_docs_dir_paths(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    root = docs / "service" / "user-guide"
    write(
        root / "index.md",
        linked(
            "Guide",
            "https://example.com/guide",
            [("Models at a glance", "old-name")],
        ),
    )
    write(
        root / "old-name" / "index.md",
        linked("Models at a glance", "https://example.com/models", []),
    )
    mkdocs = tmp_path / "mkdocs.yml"
    mkdocs.write_text(
        "- Models: service/user-guide/old-name/index.md\n"
        "- Also: docs/service/user-guide/old-name/index.md\n",
        encoding="utf-8",
    )
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "user-guide.plan.yaml").read_text(encoding="utf-8")
    )
    rename = next(
        action
        for action in plan["actions"]
        if action["op"] == "rename_directory"
    )
    assert any(link.endswith("mkdocs.yml") for link in rename["links"])
    assert main(["apply", str(root)]) == 0
    text = mkdocs.read_text(encoding="utf-8")
    assert "service/user-guide/models-at-a-glance/index.md" in text
    assert "docs/service/user-guide/models-at-a-glance/index.md" in text
    assert "old-name" not in text


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


def test_apply_skip_leaves_ready_id(
    tmp_path: Path,
    capsys,
) -> None:
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
    parent_rename = next(
        action
        for action in plan["actions"]
        if action["op"] == "rename_directory"
        and action["from"] == "wrong-parent"
    )
    assert main(["apply", str(root), "--skip", str(parent_rename["id"])]) == 0
    captured = capsys.readouterr()
    assert "applied: 1" in captured.out
    assert "left: 1" in captured.out
    assert (root / "wrong-parent" / "child" / "index.md").is_file()
    assert not (root / "parent").exists()


def test_apply_op_rename_only_skips_child_links(
    tmp_path: Path,
    capsys,
) -> None:
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
        linked("Models", "https://example.com/models", []),
    )
    write(
        root / "models" / "alpha" / "index.md",
        linked("Alpha", "https://example.com/alpha", []),
    )
    assert main(["plan", str(root)]) == 1
    plan = yaml.safe_load(
        (root / "guide.plan.yaml").read_text(encoding="utf-8")
    )
    assert any(
        action["op"] == "add_child_link" for action in plan["actions"]
    )
    assert (
        main(["apply", str(root), "--op", "rename_directory"]) == 0
    )
    captured = capsys.readouterr()
    assert "applied: 0" in captured.out
    assert "left: 1" in captured.out
    parent = (root / "models" / "index.md").read_text(encoding="utf-8")
    assert "(alpha/index.md)" not in parent


def test_apply_add_child_link_creates_child_pages_section(
    tmp_path: Path,
) -> None:
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
        linked("Models", "https://example.com/models", [])
        + "\nProse stays here.\n",
    )
    write(
        root / "models" / "alpha" / "index.md",
        linked("Alpha", "https://example.com/alpha", []),
    )
    assert main(["plan", str(root)]) == 1
    assert main(["apply", str(root), "--op", "add_child_link"]) == 0
    parent = (root / "models" / "index.md").read_text(encoding="utf-8")
    assert "Prose stays here." in parent
    assert "## Child pages" in parent
    assert "- [Alpha](alpha/index.md)" in parent
    assert parent.index("Prose stays here.") < parent.index(
        "## Child pages"
    )
    assert parent.index("## Child pages") < parent.index(
        "- [Alpha](alpha/index.md)"
    )


def test_apply_add_child_link_uses_existing_section(
    tmp_path: Path,
) -> None:
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
        "# [Models](https://example.com/models)\n\n"
        "## Providers\n\n"
        "- [Beta](beta/index.md)\n\n"
        "## Child pages\n\n"
        "- [Alpha](alpha/index.md)\n",
    )
    write(
        root / "models" / "alpha" / "index.md",
        linked("Alpha", "https://example.com/alpha", []),
    )
    write(
        root / "models" / "beta" / "index.md",
        linked("Beta", "https://example.com/beta", []),
    )
    write(
        root / "models" / "gamma" / "index.md",
        linked("Gamma", "https://example.com/gamma", []),
    )
    assert main(["plan", str(root)]) == 1
    assert main(["apply", str(root), "--op", "add_child_link"]) == 0
    parent = (root / "models" / "index.md").read_text(encoding="utf-8")
    assert parent.count("## Child pages") == 1
    assert "- [Gamma](gamma/index.md)" in parent
    providers = parent.index("## Providers")
    child_pages = parent.index("## Child pages")
    gamma = parent.index("- [Gamma](gamma/index.md)")
    assert providers < child_pages < gamma
    assert "- [Beta](beta/index.md)" in parent[
        providers:child_pages
    ]

"""Tests for the CLI entry point."""

from __future__ import annotations

from pathlib import Path

from doc_tree.cli import main


def test_dry_run_exits_zero(tmp_path: Path, capsys) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(
        "Overview: https://example.com/overview.md\n",
        encoding="utf-8",
    )
    code = main(
        [
            "scaffold",
            "--structure",
            str(structure),
            "--output",
            str(tmp_path / "out"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Pages: 1" in captured.out
    assert "Dry run" in captured.out
    assert not (tmp_path / "out").exists()


def test_scaffold_writes_files(tmp_path: Path) -> None:
    structure = tmp_path / "guide.yaml"
    structure.write_text(
        "Overview: https://example.com/overview.md\n",
        encoding="utf-8",
    )
    output = tmp_path / "out"
    code = main(
        [
            "scaffold",
            "--structure",
            str(structure),
            "--output",
            str(output),
            "--section-title",
            "Guide",
            "--section-url",
            "https://example.com/",
        ]
    )
    assert code == 0
    assert (output / "index.md").is_file()
    assert (output / "overview" / "index.md").is_file()

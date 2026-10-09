# Usage

`doc-tree` has four subcommands: `scaffold`, `validate`, `plan`, and
`apply`.

## Scaffold

```bash
doc-tree scaffold --structure PATH.yaml --output PATH [options]
```

## Required flags

| Flag | Meaning |
| --- | --- |
| `--structure PATH` | YAML file that describes the documentation tree |
| `--output PATH` | Directory that receives the generated pages |

The output directory is created when missing. Its name comes from
`--output`. Each page inside it becomes a subdirectory named from the
page title: lowercase, with each run of non-alphanumeric characters
turned into one hyphen. Every subdirectory contains `index.md`.

A source URL does not need a filename. `https://example.com/docs/`
with the title `Overview` is still written to `overview/`.

## Section index

Use both of these flags to write `output/index.md` and place the YAML
top-level pages under that section:

| Flag | Meaning |
| --- | --- |
| `--section-title TEXT` | Heading text for the section page |
| `--section-url URL` | Link target for the section heading |

Omit both flags to write the YAML top-level pages directly into
`--output`.

## Safety and progress

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Print page count, depth, and longest path; write nothing |
| `--force` | Replace existing `index.md` files |
| `--progress N` | Print `Wrote k/total pages` every N pages |

Without `--force`, an existing `index.md` stops the command before any
files are replaced.

## Optional MkDocs nav

| Flag | Meaning |
| --- | --- |
| `--nav FILE` | MkDocs config file to update |
| `--nav-parent TITLE` | Existing leaf nav title that receives the tree |
| `--docs-prefix PATH` | Path prefix relative to the MkDocs `docs_dir` |

All three flags are required together when you want nav updates. The
parent must currently be a leaf entry such as:

```yaml
- Bedrock: amazon-web-services/machine_learning/bedrock/index.md
```

`doc-tree` replaces that leaf with a nested block. The original parent
page stays first. When `--section-title` is set, the section index is
listed next, then the YAML pages.

`--docs-prefix` is the path under `docs_dir` where the pages were
written, without a leading slash. Example:

```text
amazon-web-services/machine_learning/bedrock/user-guide
```

Nav updates are optional. Large sidebars are a separate concern from
creating the files.

## Validate

```bash
doc-tree validate <directory>
```

`validate` classifies a documentation directory and prints one YAML
document. It writes no plan file and no structure YAML.

| Field | Meaning |
| --- | --- |
| `ok` | `true` only when there are no actions |
| `actions` | Count of each op that appears |
| `blocked` | Blocked rows in full |

Ready actions are counts only. Exit `0` when `ok` is true. Exit `1`
when actions remain. Use `validate` to see what still needs an agent
edit before you run `plan`.

## Plan

```bash
doc-tree plan <directory> [--plan PATH]
```

`plan` reads a documentation directory and writes
`<directory>/<dirname>.plan.yaml`. `--plan` overrides that path. The
command prints the plan path.

The directory you pass keeps its name. Its `index.md` is the section
page, so that title is not a key in the structure YAML. Child
directories are expected to use the title slug.

Exit `1` while `actions` is non-empty. Exit `0` rewrites the plan file
with `ok: true` and an empty `actions` list, then writes
`<directory>/<dirname>.yaml`.

Ready actions are listed deepest first:

| Action | Meaning |
| --- | --- |
| `rename_directory` | The folder slug differs from the H1 title |
| `add_child_link` | A child directory is missing from the parent list |
| `remove_child_link` | The parent lists a directory that is not there |

`rename_directory` records every Markdown file in the tree whose
relative link resolves to that directory, plus `mkdocs.yml` when it
contains the old path. `validate` skips that link scan. `plan` runs it
so `apply` can rewrite the listed paths.

Blocked actions stay in the file for a person or agent to resolve:

| Action | Meaning |
| --- | --- |
| `create_index` | The directory has no `index.md` |
| `need_source_url` | The file has no source URL and `local` is not `true` |
| `set_h1_link` | The H1 is not a clean title link, and a source URL is already in the file |
| `slug_collision` | Two siblings would share one path from `docs/` |

`set_h1_link` is blocked so `apply` does not rewrite the heading. Fix
the H1 to `# [Title](url)`, then run `validate` again. Until that page
is fixed, `plan` also skips rename and child-link actions that depend
on that heading.

The same slug under different parents is allowed. Two children of one
parent that slugify to the same name are a collision. `plan` does not
pick a new title.

A page with no source URL is valid when its `index.md` sets
`local: true` in frontmatter. `plan` does not invent that flag.

## Apply

```bash
doc-tree apply <directory> [--plan PATH] [--op OP]... [--skip ID]...
```

`apply` reads the plan file and performs mechanical ready actions in
the order written. The default ops are:

| Action | Meaning |
| --- | --- |
| `rename_directory` | Rename the folder, then rewrite the listed links |
| `add_child_link` | Add a missing child link under `## Child pages` |
| `remove_child_link` | Remove a parent link whose directory is gone |

`add_child_link` always writes under a `## Child pages` heading. When
that heading is missing, `apply` creates it at the end of the parent
page. Existing child bullets under other headings are left alone.
`scaffold` writes the same heading when a parent has children.

Parents may also keep a decision table (or other prose) above that
list. That is intentional. The table is for an agent choosing among
children, for example which Cohere model to use. `## Child pages` is
the structure map for `doc-tree` and for a human scanning the page.
`apply` does not remove or rewrite those tables.

| Flag | Meaning |
| --- | --- |
| `--op OP` | Perform only this mechanical op. Repeatable |
| `--skip ID` | Leave this ready action id unapplied. Repeatable |

`--op` may only name the three ops above. `--skip` requires a ready
id from the current plan file. A missing or blocked id is an error.

Selected actions stay in file order. Deepest renames still run before
shallower link edits. `apply` does not invent a title, a URL, or an
action, does not edit blocked rows, and does not rewrite the plan
file. It prints `applied` and `left`. `left` is the number of ready
actions that were not run.

`--op add_child_link` without the renames can write links to slug
folders that are not there yet. The default set avoids that because
renames are listed first. Run `validate` or `plan` again after
`apply`.

## Examples

Dry run:

```bash
doc-tree scaffold \
  --structure examples/guide.yaml \
  --output /tmp/guide \
  --section-title "Example Guide" \
  --section-url https://example.com/docs/ \
  --dry-run
```

Write pages:

```bash
doc-tree scaffold \
  --structure examples/guide.yaml \
  --output /tmp/guide \
  --section-title "Example Guide" \
  --section-url https://example.com/docs/ \
  --progress 100
```

Write pages and insert MkDocs nav:

```bash
doc-tree scaffold \
  --structure guide.yaml \
  --output docs/service/user-guide \
  --section-title "User Guide" \
  --section-url https://example.com/docs/ \
  --nav mkdocs.yml \
  --nav-parent Service \
  --docs-prefix service/user-guide \
  --force
```

Validate, plan, then apply the ready edits:

```bash
doc-tree validate docs/service/user-guide
doc-tree plan docs/service/user-guide
doc-tree apply docs/service/user-guide
doc-tree validate docs/service/user-guide
```

Apply only renames, or skip one ready id:

```bash
doc-tree apply docs/service/user-guide --op rename_directory
doc-tree apply docs/service/user-guide --skip 12
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. `plan` also writes the structure YAML when clean |
| `1` | Validation or write error, or actions remain |
| `2` | Argument parse error |

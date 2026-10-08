# Usage

`doc-tree` has three subcommands: `scaffold`, `plan`, and `apply`.

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
| `set_h1_link` | Plain H1, `local` unset, and a source URL is already in the file |

`rename_directory` records every Markdown file in the tree whose
relative link resolves to that directory, plus `mkdocs.yml` when it
contains the old path.

Blocked actions stay in the file for a person to resolve:

| Action | Meaning |
| --- | --- |
| `create_index` | The directory has no `index.md` |
| `need_source_url` | The file has no source URL and `local` is not `true` |
| `slug_collision` | Two siblings would share one path from `docs/` |

The same slug under different parents is allowed. Two children of one
parent that slugify to the same name are a collision. `plan` does not
pick a new title.

A page with no source URL is valid when its `index.md` sets
`local: true` in frontmatter. `plan` does not invent that flag.

## Apply

```bash
doc-tree apply <directory> [--plan PATH]
```

`apply` reads the plan file and performs only `status: ready` actions,
in the order written. It renames a directory, then rewrites the listed
links. It does not invent a title, a URL, or an action, and it does not
edit blocked rows. Run `plan` again after `apply`.

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

Plan a directory, then apply the ready edits:

```bash
doc-tree plan docs/service/user-guide
doc-tree apply docs/service/user-guide
doc-tree plan docs/service/user-guide
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. `plan` also writes the structure YAML |
| `1` | Validation or write error, or `plan` still has actions |
| `2` | Argument parse error |


## Required flags

| Flag | Meaning |
| --- | --- |
| `--structure PATH` | YAML file that describes the documentation tree |
| `--output PATH` | Directory that receives the generated pages |

The output directory is created when missing. Each page becomes a
subdirectory named from the page URL filename, with `.md` or `.html`
removed. Every subdirectory contains `index.md`.

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

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Validation or write error |
| `2` | Argument parse error |

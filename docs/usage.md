# Usage

The only subcommand is `scaffold`.

```bash
doc-tree scaffold --structure PATH.yaml --output PATH [options]
```

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

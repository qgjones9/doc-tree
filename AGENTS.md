# Doc tree

This repository is the tool for a large documentation tree. Use it to scaffold pages from YAML and to repair structure. The decisions repo is the tree it keeps clean.

Read [docs/usage.md](docs/usage.md) for `scaffold`, `validate`, `plan`, and `apply`. Read [docs/yaml-format.md](docs/yaml-format.md) for the YAML shape.

| Command | Use it when |
| --- | --- |
| `scaffold` | Creating the directories and `index.md` files from a YAML tree |
| `validate` | Checking compliance without writing a plan file |
| `plan` | Listing renames and child-link edits |
| `apply` | Performing the mechanical ready actions Quincy named |

`apply` writes child links under `## Child pages`. A decision table above that list stays in place. `apply` does not invent a title or a URL.

Quincy decides when `apply` runs on a real tree. Default to a dry run or a copy until he says to write the tree.

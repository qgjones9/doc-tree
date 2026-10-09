# Doc Tree

`doc-tree` turns a title-and-URL YAML tree into nested documentation
directories. Each page becomes a directory that contains a single
`index.md` with a linked heading. Parent pages also list their children.

The command is document-agnostic. Point it at any YAML file that follows
the [YAML format](docs/yaml-format.md), and it writes the tree under the
directory you choose.

## Install

Requires Python 3.11 or newer. On Linux, install with [pipx](https://pipx.pypa.io/)
so the command is isolated and available on your `PATH` from any
directory:

```bash
pipx install .
doc-tree --help
```

From a clone of this repository, run that command in the repository
root. See [Install](docs/install.md) for upgrades, uninstall, and a
`--user` install without pipx.

## Quick example

```bash
doc-tree scaffold \
  --structure examples/guide.yaml \
  --output /tmp/guide \
  --section-title "Example Guide" \
  --section-url https://example.com/docs/ \
  --dry-run
```

Remove `--dry-run` to write the directories. The example YAML lives at
[`examples/guide.yaml`](examples/guide.yaml).

## Documentation

| Guide | Contents |
| --- | --- |
| [Install](docs/install.md) | pipx, user install, upgrade, uninstall |
| [Usage](docs/usage.md) | Scaffold, validate, plan, apply, and flags |
| [YAML format](docs/yaml-format.md) | Title, URL, parent, and child rules |

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT. See [LICENSE](LICENSE).

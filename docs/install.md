# Install

`doc-tree` is a console command. After install, run it from any working
directory and pass absolute or relative paths to your YAML file and
output directory.

## Requirements

- Python 3.11 or newer
- Linux or another POSIX environment where console scripts land on
  `PATH`

## Recommended: pipx

[pipx](https://pipx.pypa.io/) installs the package into an isolated
environment and puts `doc-tree` on your `PATH`.

From a clone of this repository:

```bash
cd /path/to/doc-tree
pipx install .
doc-tree --version
```

From a published package name, once the project is on PyPI:

```bash
pipx install doc-tree
```

Confirm the command works outside the repository:

```bash
cd ~
doc-tree scaffold --help
```

## Alternative: pip --user

When pipx is not available:

```bash
cd /path/to/doc-tree
python3 -m pip install --user .
```

Ensure your user script directory is on `PATH`. On many Linux systems
that directory is `~/.local/bin`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add that line to `~/.bashrc` or `~/.zshrc` so new shells keep it.

## Upgrade

With pipx:

```bash
pipx upgrade doc-tree
```

Or reinstall from a local clone after pulling updates:

```bash
pipx install --force .
```

With pip:

```bash
python3 -m pip install --user --upgrade .
```

## Uninstall

```bash
pipx uninstall doc-tree
```

Or:

```bash
python3 -m pip uninstall doc-tree
```

## Editable install for development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
doc-tree --help
pytest
```

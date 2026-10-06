"""Allow ``python -m doc_tree`` to invoke the CLI."""

from doc_tree.cli import main

raise SystemExit(main())

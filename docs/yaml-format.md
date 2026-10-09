# YAML format

`doc-tree` reads one YAML mapping. Key order is the page order.

## Leaf page

A key is the page title. A string value is the page URL:

```yaml
Overview: https://example.com/docs/overview.md
Quickstart: https://example.com/docs/quickstart.md
```

The directory name comes from the page title, not the URL. The title
is lowercased, each run of non-alphanumeric characters becomes one
hyphen, and hyphens are stripped from the ends:

| Title | Directory |
| --- | --- |
| `Overview` | `overview` |
| `Models at a glance` | `models-at-a-glance` |

A URL does not need a filename. The folder still comes from the title.

## Parent page

A mapping value is a parent. It contains `url`, or `local: true` when
there is no source URL. Every other key is a child page in the same
shape:

```yaml
Models:
  url: https://example.com/docs/models.md
  Alpha:
    url: https://example.com/docs/models-alpha.md
    Alpha One: https://example.com/docs/model-alpha-one.md
  Beta: https://example.com/docs/models-beta.md
```

Nesting can continue as deep as you need. Parents are written before
their children.

## Generated page text

Each `index.md` starts with a linked heading:

```markdown
# [Overview](https://example.com/docs/overview.md)
```

A parent then lists its direct children under `## Child pages`:

```markdown
# [Models](https://example.com/docs/models.md)

## Child pages

- [Alpha](alpha/index.md)
- [Beta](beta/index.md)
```

## Local page

A page you wrote, with no source URL, sets `local: true`. `local` is
the first key. `url` is omitted:

```yaml
A note I wrote:
  local: true
Notes:
  local: true
  Detail:
    local: true
```

`scaffold` writes frontmatter and a plain H1:

```markdown
---
local: true
---
# A note I wrote
```

A page may set `local: true` and still include `url`. The heading stays
linked. The flag means the URL is optional.

## Rejected input

The command stops before writing when:

- The structure file is missing, empty, or not a mapping
- A page has no URL and `local` is not `true`
- A parent mapping omits `url` and `local`
- Two siblings would share the same directory slug
- A title has no letters or digits to form a slug

## Complete example

See [`examples/guide.yaml`](../examples/guide.yaml).

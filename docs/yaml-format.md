# YAML format

`doc-tree` reads one YAML mapping. Key order is the page order.

## Leaf page

A key is the page title. A string value is the page URL:

```yaml
Overview: https://example.com/docs/overview.md
Quickstart: https://example.com/docs/quickstart.md
```

The directory name comes from the URL filename with `.md` or `.html`
removed:

| URL | Directory |
| --- | --- |
| `https://example.com/docs/overview.md` | `overview` |
| `.../model-card-amazon-nova-premier.html` | `model-card-amazon-nova-premier` |

## Parent page

A mapping value is a parent. It must contain `url`. Every other key is a
child page in the same shape:

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

A parent then lists its direct children:

```markdown
# [Models](https://example.com/docs/models.md)

- [Alpha](models-alpha/index.md)
- [Beta](models-beta/index.md)
```

## Rejected input

The command stops before writing when:

- The structure file is missing, empty, or not a mapping
- A page has no URL
- A parent mapping omits `url`
- Two siblings would share the same directory name
- A URL has no usable filename

## Complete example

See [`examples/guide.yaml`](../examples/guide.yaml).

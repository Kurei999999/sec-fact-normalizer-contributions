"""Display an archetype JSON as a tree, optionally saving it as UTF-8 text."""

import argparse
import json
from pathlib import Path


def iter_nodes(nodes, prefix=""):
    """Yield each node and its concepts, then recursively visit its children."""
    for position, node in enumerate(nodes):
        last = position == len(nodes) - 1
        branch = "└── " if last else "├── "
        child_prefix = prefix + ("    " if last else "│   ")
        concepts = node["concepts"]
        review_mark = " *" if any(c["status"] == "review" for c in concepts) else ""
        label = node.get("label") or node["node_id"]
        yield f"{prefix}{branch}{label} [{node['node_kind']}]{review_mark}"
        for concept in concepts:
            yield f"{child_prefix}concept: {concept['name']}"
        yield from iter_nodes(node.get("children", []), child_prefix)


def render_tree(document):
    """Return the complete presentation tree without inferring calculations."""
    lines = [
        f"{document['profile_id']} — {document['statement']}",
        "Types: [total], [group], [line_item]; * = review",
        "",
        *iter_nodes(document["nodes"]),
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Archetype JSON file")
    parser.add_argument("--output", "-o", type=Path, help="Save to a UTF-8 text file")
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.path.resolve():
        parser.error("Output must differ from the input JSON file")
    try:
        document = json.loads(args.path.read_text(encoding="utf-8"))
        tree = render_tree(document)
    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ) as exc:
        parser.exit(1, f"Cannot render archetype: {exc}\n")
    if args.output:
        try:
            args.output.write_text(tree, encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            parser.exit(1, f"Cannot write tree: {exc}\n")
        print(f"Saved: {args.output}")
    else:
        print(tree, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

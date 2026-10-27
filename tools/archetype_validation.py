"""Validate presentation structure; this does not validate accounting semantics."""

import argparse
import json
from pathlib import Path


def validate_archetype(document, *, strict=None, expected_concepts=None):
    """Keep legacy profiles valid; typed profiles require leaf and metadata rules.

    expected_concepts optionally checks coverage against an independent source.
    Totals describe presentation, never an instruction to sum their children.
    """
    errors = []
    empty_groups = []
    node_ids = set()
    concepts = {}
    if strict is None:
        strict = isinstance(document, dict) and document.get("validation_profile") == "typed_balance_sheet"

    def visit(nodes, path, in_supplement=False):
        if not isinstance(nodes, list):
            errors.append(f"{path}: expected a node list")
            return
        for position, node in enumerate(nodes):
            location = f"{path}[{position}]"
            if not isinstance(node, dict):
                errors.append(f"{location}: expected a node object")
                continue
            supplemental = in_supplement or node.get("node_id") == "supplementary_disclosures"
            required = {
                "node_id", "metric_id", "label", "node_kind", "concepts",
                "aggregation_policy",
            }
            missing = required - node.keys()
            if missing:
                errors.append(f"{location}: missing {', '.join(sorted(missing))}")
            node_id = node.get("node_id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"{location}: node_id must be a nonempty string")
            elif node_id in node_ids:
                errors.append(f"{location}: duplicate node_id {node_id}")
            else:
                node_ids.add(node_id)
            kind = node.get("node_kind")
            if kind not in {"group", "line_item", "analytical", "total", "subtotal"}:
                errors.append(f"{location}: unsupported node_kind {kind!r}")
            if kind in {"group", "analytical"} and node.get("metric_id") is not None:
                errors.append(f"{location}: {kind} metric_id must be null")
            fact_kind = kind in {"line_item", "total", "subtotal"}
            if fact_kind and node.get("metric_id") != node_id:
                errors.append(f"{location}: {kind} metric_id must equal node_id")
            if node.get("aggregation_policy") != "none":
                errors.append(f"{location}: aggregation_policy must be none")
            entries = node.get("concepts", [])
            if not isinstance(entries, list):
                errors.append(f"{location}: concepts must be a list")
                entries = []
            if fact_kind and not entries:
                errors.append(f"{location}: {kind} requires at least one concept")
            if strict and kind == "group" and entries:
                errors.append(f"{location}: group must not contain concepts")
            if strict and fact_kind:
                if node.get("period_type") not in {"instant", "duration"}:
                    errors.append(f"{location}: missing or invalid period_type")
                if node.get("unit_type") not in {"monetary", "shares", "per_share", "percent"}:
                    errors.append(f"{location}: missing or invalid unit_type")
                if type(node.get("contra")) is not bool:
                    errors.append(f"{location}: missing or invalid contra boolean")
                if not supplemental and (node.get("period_type") != "instant" or node.get("unit_type") != "monetary"):
                    errors.append(f"{location}: primary BS facts must be instant monetary balances")
                if node.get("contra") is True and node.get("unit_type") != "monetary":
                    errors.append(f"{location}: contra balance must be monetary")
            for entry in entries:
                name = entry.get("name") if isinstance(entry, dict) else None
                if not isinstance(name, str) or not name:
                    errors.append(f"{location}: concept requires a nonempty name")
                elif name in concepts:
                    errors.append(f"{location}: duplicate concept {name} (first at {concepts[name]})")
                else:
                    concepts[name] = location
                if strict and isinstance(entry, dict):
                    if entry.get("status") not in {"proposed", "review"}:
                        errors.append(f"{location}: invalid concept status")
                    if entry.get("status") == "review":
                        reason = entry.get("review_reason")
                        if not isinstance(reason, str) or not reason.strip():
                            errors.append(f"{location}: review concept requires review_reason")
            children = node.get("children", [])
            if strict and kind == "line_item" and children:
                errors.append(f"{location}: line_item must not have children; use total/subtotal or group")
            if kind == "group" and children == []:
                empty_groups.append(node_id)
            visit(children, f"{location}.children", supplemental)

    if not isinstance(document, dict):
        return ["document must be an object"], []
    if "nodes" not in document:
        errors.append("document requires nodes")
    visit(document.get("nodes", []), "nodes")
    if expected_concepts is not None:
        expected = set(expected_concepts)
        for name in sorted(expected - concepts.keys()):
            errors.append(f"missing expected concept {name}")
        for name in sorted(concepts.keys() - expected):
            errors.append(f"unexpected concept {name}")
    if document.get("schema_version") == "1.4.0":
        from archetype_format import validate_format
        errors.extend(validate_format(document))
    return errors, empty_groups


def missing_metadata(document):
    """Report concept-bearing nodes only; structural groups have no fact units."""
    missing = {key: [] for key in ("period_type", "unit_type", "contra")}

    def visit(nodes):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("concepts"):
                for key in missing:
                    if key not in node or node[key] is None:
                        missing[key].append(node.get("node_id"))
            children = node.get("children", [])
            if isinstance(children, list):
                visit(children)

    if isinstance(document, dict) and isinstance(document.get("nodes"), list):
        visit(document["nodes"])
    return missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[1] / "archetypes/general_corporate/cf.json",
    )
    parser.add_argument("--strict", action="store_true", default=None,
                        help="Require typed balance-sheet rules (automatic for typed_balance_sheet profiles)")
    parser.add_argument("--expected-concepts", type=Path,
                        help="Whitespace-separated concept names for independent coverage verification")
    parser.add_argument("--metadata-report", action="store_true",
                        help="List concept-bearing nodes missing period_type, unit_type or contra")
    args = parser.parse_args()
    try:
        document = json.loads(args.path.read_text())
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot read archetype: {exc}\n")
    try:
        expected = args.expected_concepts.read_text().split() if args.expected_concepts else None
    except OSError as exc:
        parser.exit(1, f"Cannot read expected concepts: {exc}\n")
    errors, empty_groups = validate_archetype(document, strict=args.strict, expected_concepts=expected)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"Empty groups ({len(empty_groups)}; informational):")
    for node_id in empty_groups:
        print(f"  {node_id}")
    if args.metadata_report:
        for key, node_ids in missing_metadata(document).items():
            print(f"Missing {key} ({len(node_ids)}):")
            for node_id in node_ids:
                print(f"  {node_id}")
    print(f"Validation: {'FAILED' if errors else 'PASSED'} ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

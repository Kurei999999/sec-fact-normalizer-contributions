"""Validate API normalization rules and per-industry dependencies, not accounting meaning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
import json


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children", []))


def validate_contract(document, base_dir):
    errors = []
    fields = [m["field"] for m in document["metrics"]]
    if len(fields) != len(set(fields)):
        errors.append("Duplicate metric field")
    metadata = [m["field"] for m in document.get("metadata_fields", [])]
    if len(metadata + fields) != len(set(metadata + fields)):
        errors.append("Duplicate metadata or metric field")
    metrics = {m["field"]: m for m in document["metrics"]}
    profiles = document["source_profiles"]
    nodes = {}
    for profile, rel in profiles.items():
        try:
            source = json.loads((Path(base_dir) / rel).read_text())
            nodes[profile] = {n["node_id"]: n for n in walk(source["nodes"])}
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"{profile}: cannot load source profile: {exc}")
            nodes[profile] = {}
    graphs = {p: {field: set() for field in fields} for p in profiles}
    rule_ids = set()
    for field, metric in metrics.items():
        if not metric.get("definition"):
            errors.append(f"{field}: missing definition")
        if "derivation" in metric:
            errors.append(f"{field}: legacy derivation must be migrated into rules")
        if set(metric["source_mappings"]) != set(profiles):
            errors.append(f"{field}: profile set does not match source_profiles")
        for profile, mapping in metric["source_mappings"].items():
            if profile not in profiles:
                continue
            priorities = set()
            rules = mapping.get("rules", [])
            for rule in rules:
                location = f'{field}/{profile}/{rule.get("rule_id")}'
                rule_id = rule.get("rule_id")
                if not isinstance(rule_id, str) or not rule_id or rule_id in rule_ids:
                    errors.append(f"{location}: missing or duplicate rule ID")
                rule_ids.add(rule_id)
                priority = rule.get("priority")
                if type(priority) is not int or priority < 0 or priority in priorities:
                    errors.append(f"{location}: invalid or duplicate priority")
                priorities.add(priority)
                conditions = rule.get("requires")
                if (
                    not isinstance(conditions, list)
                    or not conditions
                    or any(not isinstance(x, str) or not x.strip() for x in conditions)
                ):
                    errors.append(f"{location}: nonempty condition list required")
                method = rule.get("method")
                if method == "direct":
                    refs = [rule]
                elif method == "calculation":
                    refs = rule.get("inputs", [])
                    if (
                        rule.get("operation") not in {"sum", "subtract"}
                        or len(refs) < 2
                    ):
                        errors.append(f"{location}: invalid operation or input count")
                    if metric.get("calculation_policy", {}).get("allowed") is False:
                        errors.append(
                            f"{location}: calculation exists despite disabled policy"
                        )
                    resolved = [
                        ref.get("metric_id")
                        for ref in refs
                        if ref.get("source_type") == "resolved_metric"
                    ]
                    if resolved and len(resolved) != len(refs):
                        errors.append(
                            f"{location}: cannot mix raw and resolved metric inputs"
                        )
                    if resolved:
                        separator = " + " if rule.get("operation") == "sum" else " - "
                        if rule.get("expression") != separator.join(resolved):
                            errors.append(
                                f"{location}: expression disagrees with operation/input order"
                            )
                else:
                    errors.append(f"{location}: unsupported method")
                    continue
                for ref in refs:
                    source_type = ref.get("source_type", "mapped_node")
                    if source_type == "resolved_metric":
                        target = ref.get("metric_id")
                        if method != "calculation" or target not in metrics:
                            errors.append(
                                f"{location}: invalid resolved metric {target}"
                            )
                            continue
                        graphs[profile][field].add(target)
                        target_metric = metrics[target]
                        if target_metric.get("unit_type") != metric.get(
                            "unit_type"
                        ) or target_metric.get("period_type") != metric.get(
                            "period_type"
                        ):
                            errors.append(
                                f"{location}: incompatible resolved input metadata"
                            )
                        if (
                            not target_metric["source_mappings"]
                            .get(profile, {})
                            .get("rules")
                        ):
                            errors.append(
                                f"{location}: resolved input has no rules for profile"
                            )
                    elif source_type == "raw_concept":
                        if ref.get("source_status") != "review" or ":" not in ref.get(
                            "concept", ""
                        ):
                            errors.append(
                                f"{location}: supplemental raw concept must be review status and qualified"
                            )
                    elif source_type == "mapped_node":
                        node = nodes[profile].get(ref.get("node_id"))
                        if node is None:
                            errors.append(
                                f'{location}: unknown node {ref.get("node_id")}'
                            )
                            continue
                        if not any(
                            c["name"] == ref.get("concept")
                            and c.get("status", "proposed") == ref.get("source_status")
                            for c in node.get("concepts", [])
                        ):
                            errors.append(
                                f"{location}: concept/status does not match source node"
                            )
                        if node.get("period_type") != metric.get(
                            "period_type"
                        ) or node.get("unit_type") != metric.get("unit_type"):
                            errors.append(
                                f"{location}: source metadata does not match metric"
                            )
                    else:
                        errors.append(
                            f"{location}: unsupported source type {source_type}"
                        )
            if mapping.get("status") == "unsupported" and rules:
                errors.append(f"{field}/{profile}: unsupported mapping has rules")
    for profile, graph in graphs.items():
        visited, active = set(), set()

        def visit(field, path):
            if field in active:
                errors.append(
                    f'{profile}: circular dependency: {" -> ".join(path + [field])}'
                )
                return
            if field in visited:
                return
            active.add(field)
            for target in sorted(graph[field]):
                visit(target, path + [field])
            active.remove(field)
            visited.add(field)

        for field in graph:
            visit(field, [])
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "archetypes/api/is.json",
    )
    args = parser.parse_args()
    document = json.loads(args.path.read_text())
    errors = validate_contract(document, args.path.parent)
    for error in errors:
        print("ERROR:", error)
    rules = [
        r
        for m in document["metrics"]
        for s in m["source_mappings"].values()
        for r in s["rules"]
    ]
    print(
        f'{len(document["metrics"])} metrics; {len(rules)} rules; {len(errors)} errors'
    )
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

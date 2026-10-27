"""Demonstrate one direct mapping; this is not the full normalization engine."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_example():
    sample = json.loads((ROOT / "examples/revenue/raw_facts.json").read_text())
    fact = sample["facts"][0]
    document = json.loads((ROOT / "archetypes/general_corporate/is.json").read_text())

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.get("children", []))

    matches = [
        node
        for node in walk(document["nodes"])
        if any(c["name"] == fact["concept"] for c in node.get("concepts", []))
    ]
    if len(matches) != 1:
        raise ValueError("Example must map to exactly one archetype node")
    contract = json.loads((ROOT / "archetypes/api/is.json").read_text())
    metric = next(m for m in contract["metrics"] if m["field"] == "revenue")
    rules = [
        r
        for r in metric["source_mappings"][sample["profile_id"]]["rules"]
        if r["method"] == "direct"
        and r.get("concept") == fact["concept"]
        and r.get("node_id") == matches[0]["node_id"]
    ]
    if not rules:
        raise ValueError("No matching direct API rule for the sample")
    # One explicitly chosen, unambiguous observation. No competing candidates,
    # cumulative subtraction, semantic approval or global priority inference.
    result = dict(
        statement="IS",
        field="revenue",
        node_id=matches[0]["node_id"],
        concept=fact["concept"],
        value=fact["value"],
        unit=fact["unit"],
        start_date=fact["start_date"],
        end_date=fact["end_date"],
    )
    expected = json.loads((ROOT / "examples/revenue/expected.json").read_text())
    if result != expected:
        raise ValueError("Example result differs from expected output")
    return result


if __name__ == "__main__":
    print(json.dumps(run_example(), indent=2))

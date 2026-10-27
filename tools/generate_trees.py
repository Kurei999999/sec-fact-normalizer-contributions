"""Regenerate text trees from the authoritative industry JSON mappings."""

import json
from pathlib import Path
from print_mapping_tree import render_tree

ROOT = Path(__file__).resolve().parents[1]


def main():
    assignment = json.loads((ROOT / "archetypes/sic_to_archetype.json").read_text())
    lines = [
        "NORMALIZATION MAPS",
        "==================",
        "",
        "Company CIK/SIC -> industry profile -> archetype concept/node -> API field",
        "Company overrides take precedence over SIC assignments.",
        "Classification is separate from source selection, calculations and approval.",
        "Tree nesting never means automatically sum all children.",
        "",
        "Industry trees:",
    ]
    for profile, info in assignment["archetypes"].items():
        for statement, relative in info["statements"].items():
            document = json.loads((ROOT / relative).read_text())
            target = (
                ROOT / "archetypes" / profile / "trees" / f"{statement.lower()}.txt"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render_tree(document), encoding="utf-8")
            lines.append(f"  archetypes/{profile}/trees/{statement.lower()}.txt")
    lines += ["", "API FIELDS AND RULES", "===================="]
    for statement in ["is", "bs", "cf"]:
        document = json.loads((ROOT / f"archetypes/api/{statement}.json").read_text())
        lines += ["", statement.upper()]
        for metric in document["metrics"]:
            lines.append(
                f'  {metric["field"]}: {metric.get("definition", "See API contract")}'
            )
            for profile, mapping in metric["source_mappings"].items():
                lines.append(f"    {profile}:")
                if not mapping["rules"]:
                    lines.append("      No enabled structural candidate rules")
                for position, rule in enumerate(mapping["rules"], 1):
                    lines.append(
                        f'      {position}. {rule["rule_id"]} [{rule["method"]}]'
                    )
                    if rule.get("concept"):
                        lines.append(f'         concept: {rule["concept"]}')
                    if rule.get("expression"):
                        lines.append(f'         expression: {rule["expression"]}')
                    if rule.get("sign_multiplier") is not None:
                        lines.append(
                            f'         sign multiplier: {rule["sign_multiplier"]}'
                        )
    (ROOT / "docs/normalization.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("Generated 24 industry trees and docs/normalization.txt")


if __name__ == "__main__":
    main()

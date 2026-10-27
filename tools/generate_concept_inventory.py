"""Export research inventories from a read-only raw DB, using profile source SICs."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def mapped_concepts(repo, profile):
    result = {}

    def walk(nodes, statement):
        for node in nodes:
            for concept in node.get("concepts", []):
                result.setdefault(concept["name"], []).append(
                    {
                        "statement": statement,
                        "node_id": node["node_id"],
                        "label": node.get("label"),
                        "status": concept.get("status"),
                    }
                )
            walk(node.get("children", []), statement)

    assignment = read(repo / "archetypes/sic_to_archetype.json")
    for statement, relative in assignment["archetypes"][profile]["statements"].items():
        walk(read(repo / relative)["nodes"], statement)
    return result


def company_observations(connection, company_id):
    # SQLite's single MAX aggregate selects its companion bare columns from the
    # same winning row. The fact ID is a deterministic tie breaker. COUNT does
    # not participate in that selection. Group per company to bound memory.
    return connection.execute(
        """
        SELECT r.concept_id, COUNT(*) AS observation_count,
               MAX(COALESCE(f.filed_date,'') || '|' || r.end_date || '|' ||
                   f.accession || '|' || printf('%020d',r.fact_id)) AS latest_key,
               r.value, r.unit, r.start_date, r.end_date,
               f.accession, f.form, f.filed_date
        FROM filings f JOIN raw_facts r USING(filing_id)
        WHERE f.company_id=?
        GROUP BY r.concept_id
        ORDER BY r.concept_id
    """,
        (company_id,),
    )


def build_profile(
    connection, repo, profile, companies, concepts, generated_at, examples_limit=2
):
    config = read(repo / "archetypes" / profile / "profile.json")
    source_sics = config["research_scope"]["source_sics"]
    selected = [c for c in companies if c["sic"] in source_sics]
    mapped = mapped_concepts(repo, profile)
    totals = Counter(c["sic"] for c in selected)
    with_facts = Counter()
    inventory = {}
    for position, company in enumerate(selected, 1):
        observations = list(company_observations(connection, company["company_id"]))
        if observations:
            with_facts[company["sic"]] += 1
        for row in observations:
            concept = concepts[row["concept_id"]]
            name = concept["taxonomy"] + ":" + concept["tag"]
            if name not in inventory:
                inventory[name] = {
                    "concept": name,
                    "label": concept["label"] or concept["tag"],
                    "taxonomy": concept["taxonomy"],
                    "company_count": 0,
                    "observation_count": 0,
                    "company_counts_by_sic": {},
                    "mappings": mapped.get(name, []),
                    "examples": [],
                }
            item = inventory[name]
            item["company_count"] += 1
            item["observation_count"] += row["observation_count"]
            sic = company["sic"]
            item["company_counts_by_sic"][sic] = (
                item["company_counts_by_sic"].get(sic, 0) + 1
            )
            if len(item["examples"]) < examples_limit:
                accession = row["accession"]
                item["examples"].append(
                    {
                        "cik": company["cik"],
                        "ticker": company["ticker"],
                        "company_name": company["name"],
                        "sic": sic,
                        **{
                            k: row[k]
                            for k in [
                                "value",
                                "unit",
                                "start_date",
                                "end_date",
                                "accession",
                                "form",
                                "filed_date",
                            ]
                        },
                        "filing_url": f'https://www.sec.gov/Archives/edgar/data/{int(company["cik"])}/{accession.replace("-", "")}/{accession}-index.html',
                    }
                )
        if position % 50 == 0 or position == len(selected):
            print(
                f"{profile}: {position}/{len(selected)} companies inspected", flush=True
            )
    items = sorted(
        inventory.values(), key=lambda item: (-item["company_count"], item["concept"])
    )
    for item in items:
        item["company_counts_by_sic"] = dict(
            sorted(item["company_counts_by_sic"].items())
        )
        item["appearance_percentage"] = round(
            item["company_count"] / sum(with_facts.values()) * 100, 4
        )
    digest = hashlib.sha256()
    for relative in [
        "archetypes/sic_to_archetype.json",
        f"archetypes/{profile}/profile.json",
        *read(repo / "archetypes/sic_to_archetype.json")["archetypes"][profile][
            "statements"
        ].values(),
    ]:
        digest.update(relative.encode())
        digest.update((repo / relative).read_bytes())
    meta = {
        "generated_at": generated_at,
        "profile_id": profile,
        "research_scope": config["research_scope"],
        "population": {
            "companies_in_source_db": len(selected),
            "companies_with_facts": sum(with_facts.values()),
            "companies_by_sic": {sic: totals[sic] for sic in source_sics},
            "companies_with_facts_by_sic": {
                sic: with_facts[sic] for sic in source_sics
            },
        },
        "filters": {
            "minimum_appearance": None,
            "minimum_statement_rate": None,
            "period": None,
            "taxonomy": None,
            "unit": None,
            "form": None,
        },
        "mapping_scope_sha256": digest.hexdigest(),
        "notes": [
            "Research population uses source_sics only; runtime assignments and overrides do not expand it.",
            "Counts reflect this raw database snapshot, not every issuer ever assigned this SIC.",
            "Company count is distinct per concept across all filings, periods and units.",
            "Appearance percentage denominator is companies with any raw facts in this research scope.",
            "Mappings describe current archetype placement, not observed filing statement membership.",
            "CompanyFacts alone does not establish IS/BS/CF membership; no statement rate is inferred.",
            "Examples are bounded and do not limit concept inclusion. A source value can itself contain an error.",
        ],
    }
    unmapped = [item for item in items if not item["mappings"]]
    return (
        {**meta, "concept_count": len(items), "concepts": items},
        {**meta, "concept_count": len(unmapped), "concepts": unmapped},
    )


def write_profile(directory, all_concepts, unmapped):
    directory.mkdir(parents=True, exist_ok=True)
    for filename, document in [
        ("all_concepts.json", all_concepts),
        ("unmapped_concepts.json", unmapped),
    ]:
        (directory / filename).write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    p = unmapped["population"]
    lines = [
        f'{unmapped["profile_id"]}: UNMAPPED CONCEPTS',
        "=" * 60,
        "Source SICs: " + ", ".join(unmapped["research_scope"]["source_sics"]),
        f'Companies: {p["companies_in_source_db"]}; with facts: {p["companies_with_facts"]}',
        f'Unique concepts: {all_concepts["concept_count"]}; unmapped: {unmapped["concept_count"]}',
        "No frequency thresholds. Statement membership is unknown unless independently reviewed.",
        "Some concepts are disclosures that should remain outside primary statements.",
        "",
    ]
    for item in unmapped["concepts"]:
        lines += [
            item["concept"],
            "  Label: " + item["label"],
            f'  Companies: {item["company_count"]} ({item["appearance_percentage"]}% of companies with facts)',
            "  SIC breakdown: "
            + ", ".join(
                f"{sic}: {n}" for sic, n in item["company_counts_by_sic"].items()
            ),
        ]
        for example in item["examples"]:
            lines += [
                f'  Example: {example["ticker"] or example["cik"]} / CIK {example["cik"]} / SIC {example["sic"]}',
                f'    Period: {example["start_date"] or "instant"} through {example["end_date"]}',
                f'    Reported: {example["value"]} {example["unit"]}',
                "    Filing: " + example["filing_url"],
            ]
        lines += [
            "  Suggest: statement/category or outside-primary-statements, scope, evidence and reasoning.",
            "",
        ]
    (directory / "unmapped_concepts.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, required=True, help="Raw source_v2.sqlite3 (read-only)"
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="Defaults to <repo-root>/review")
    parser.add_argument(
        "--profiles", nargs="+", help="Default: every declared archetype"
    )
    parser.add_argument("--examples-per-concept", type=int, default=2)
    args = parser.parse_args()
    if args.examples_per_concept < 1:
        parser.error("At least one example is required")
    source = args.source.expanduser().resolve()
    repo = args.repo_root.expanduser().resolve()
    output = (args.output or repo / "review").expanduser().resolve()
    if not source.is_file():
        parser.error("Source database does not exist")
    profiles = list(read(repo / "archetypes/sic_to_archetype.json")["archetypes"])
    if args.profiles:
        if set(args.profiles) - set(profiles):
            parser.error("Unknown profile")
        profiles = list(dict.fromkeys(args.profiles))
    output.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    summary = {
        "status": "complete",
        "generated_at": generated,
        "profiles": {},
        "source_size": source.stat().st_size,
        "source_mtime_ns": source.stat().st_mtime_ns,
    }
    # Hold a single consistent read snapshot; never mutate the source database.
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA cache_size=-16000")
        connection.execute("BEGIN")
        companies = [
            dict(c)
            for c in connection.execute(
                "SELECT company_id,cik,ticker,name,sic FROM companies ORDER BY cik"
            )
        ]
        for company in companies:
            company["sic"] = (
                str(company["sic"]).strip().zfill(4)
                if company["sic"] is not None
                else None
            )
        concepts = {
            r["concept_id"]: dict(r)
            for r in connection.execute(
                "SELECT concept_id,taxonomy,tag,label FROM concepts"
            )
        }
        with tempfile.TemporaryDirectory(prefix="concept-inventory-") as tmp:
            staging = Path(tmp)
            for profile in profiles:
                all_items, unmapped = build_profile(
                    connection,
                    repo,
                    profile,
                    companies,
                    concepts,
                    generated,
                    args.examples_per_concept,
                )
                write_profile(staging / profile, all_items, unmapped)
                summary["profiles"][profile] = {
                    **all_items["population"],
                    "all_concepts": all_items["concept_count"],
                    "unmapped_concepts": unmapped["concept_count"],
                }
            # Existing review files are replaced only after all requested exports succeed.
            for profile in profiles:
                target = output / profile
                target.mkdir(exist_ok=True)
                for filename in [
                    "all_concepts.json",
                    "unmapped_concepts.json",
                    "unmapped_concepts.txt",
                ]:
                    temporary = target / (filename + ".tmp")
                    temporary.write_bytes((staging / profile / filename).read_bytes())
                    temporary.replace(target / filename)
    temporary = output / "inventory_summary.json.tmp"
    temporary.write_text(json.dumps(summary, indent=2) + "\n")
    temporary.replace(output / "inventory_summary.json")
    print(json.dumps(summary["profiles"], indent=2), flush=True)


if __name__ == "__main__":
    main()

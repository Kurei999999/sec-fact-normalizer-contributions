"""Based on main.py: count concepts by source SIC, add presentation evidence and definitions."""
import argparse
from datetime import datetime, timezone
import tempfile
from generate_concept_review import load_descriptions

import json
import os
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

BASE_PATH = Path(__file__).resolve().parents[1]


def find_facts_by_sic(
    sics: list[int],
    companyfacts_path: Path,
    company_info_path: Path,
):
    wanted_sics = {str(sic) for sic in sics}
    companies = json.loads(company_info_path.read_text())

    ciks = {
        int(company["cik_str"])
        for company in companies.values()
        if str(company.get("sic")) in wanted_sics
    }

    counts = Counter()
    loaded_companies = 0
    loaded_ciks = set()
    labels = {}

    for cik in sorted(ciks):
        file = companyfacts_path / f"CIK{cik:010d}.json"

        try:
            data = json.loads(file.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Skipping {file.name}: {error}")
            continue

        loaded_companies += 1
        loaded_ciks.add(str(cik))
        for taxonomy, tags in data.get("facts", {}).items():
            for tag, details in tags.items():
                labels.setdefault(f"{taxonomy}:{tag}", details.get("label") or tag)
        if loaded_companies % 50 == 0:
            print(f"Loaded {loaded_companies}/{len(ciks)} company files", flush=True)
        counts.update(
            {
                f"{taxonomy}:{tag}"
                for taxonomy, tags in data.get("facts", {}).items()
                for tag in tags
            }
        )

    if loaded_companies == 0:
        raise ValueError("No company facts were loaded for the selected SICs.")

    print(f"Loaded companies: {loaded_companies}")

    facts = [
        {
            "fact": fact,
            "label": labels[fact],
            "company_count": count,
            "appearance_percentage": round(count / loaded_companies * 100, 2),
        }
        for fact, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return facts, loaded_ciks, len(ciks)


def load_statement_rows(sec_fs_data_sets_path):
    pre = pd.read_csv(sec_fs_data_sets_path / "pre.txt", sep="\t",
                      usecols=["adsh", "version", "tag", "stmt"], dtype=str)
    sub = pd.read_csv(sec_fs_data_sets_path / "sub.txt", sep="\t",
                      usecols=["adsh", "cik", "sic"], dtype=str)
    pre = pre.loc[pre["version"].str.startswith("us-gaap/", na=False)]
    sub["sic"] = sub["sic"].str.zfill(4)
    sub["cik"] = sub["cik"].str.lstrip("0")
    df = pre.merge(sub, on="adsh", how="inner", validate="many_to_one")
    df["concept"] = "us-gaap:" + df["tag"]
    return df


def add_statement_info(facts, sics, rows, loaded_ciks):
    df = rows.loc[rows["sic"].isin({str(s).zfill(4) for s in sics}) & rows["cik"].isin(loaded_ciks)]
    concepts = {item["fact"] for item in facts}
    matched = df.loc[df["concept"].isin(concepts)]

    totals = matched.groupby(["sic", "concept"])["cik"].nunique()
    counts = matched.groupby(["sic", "concept", "stmt"])["cik"].nunique()

    rates_by_concept = {}
    for (sic, concept, stmt), count in counts.items():
        total = int(totals.loc[(sic, concept)])
        rates_by_concept.setdefault(concept, []).append(
            {
                "sic": sic,
                "stmt": stmt,
                "company_count": int(count),
                "concept_company_count": total,
                "statement_rate": int(count) / total,
            }
        )

    statements_by_concept = (
        matched.dropna(subset=["stmt"])
        .groupby("concept")["stmt"]
        .agg(lambda values: sorted(set(values)))
        .to_dict()
    )

    return [
        {
            **item,
            "stmt": statements_by_concept.get(item["fact"], []),
            "statement_rates": rates_by_concept.get(item["fact"], []),
        }
        for item in facts
    ]


def group_facts_by_statement(facts):
    grouped = {statement: [] for statement in ("BS", "IS", "CF", "unclassified")}
    for fact in facts:
        observed = set(fact.get("stmt", [])) & {"BS", "IS", "CF"}
        for statement in sorted(observed):
            grouped[statement].append(fact)
        if not observed:
            grouped["unclassified"].append(fact)
    return grouped


def collect_mapped(nodes):
    result = set()
    for node in nodes:
        result.update(concept["name"] for concept in node.get("concepts", []))
        result.update(collect_mapped(node.get("children", [])))
    return result


def write_review_files(directory, facts, grouped, metadata, maps):
    """Preserve main.py's list/dictionary formats; put provenance in its own file."""
    mapped_anywhere = set().union(*maps.values())
    unmapped_by_sic = [fact for fact in facts if fact["fact"] not in mapped_anywhere]
    unmapped_by_statement = {}
    for statement, observed in grouped.items():
        mapped = maps.get(statement, mapped_anywhere)
        unmapped_by_statement[statement] = [fact for fact in observed if fact["fact"] not in mapped]
    documents = {
        "facts_by_sic.json": facts,
        "facts_by_statement.json": grouped,
        "unmapped_facts_by_sic.json": unmapped_by_sic,
        "unmapped_facts_by_statement.json": unmapped_by_statement,
        "metadata.json": metadata,
    }
    directory.mkdir(parents=True, exist_ok=True)
    for name, document in documents.items():
        (directory / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {statement: {"observed_unique": len(grouped[statement]), "unmapped": len(missing)}
            for statement, missing in unmapped_by_statement.items()}


def main():
    load_dotenv(Path.cwd() / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companyfacts-dir", type=Path, default=os.getenv("COMPANYFACTS_PATH"))
    parser.add_argument("--statements-dir", type=Path, default=os.getenv("SEC_FS_DATA_SETS_PATH"))
    parser.add_argument("--company-info", type=Path, required=True)
    parser.add_argument("--taxonomy-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=BASE_PATH)
    parser.add_argument("--profiles", nargs="+")
    args = parser.parse_args()
    if not args.companyfacts_dir or not args.statements_dir:
        parser.error("Pass --companyfacts-dir and --statements-dir, or set the corresponding .env values")
    repo = args.repo_root.expanduser().resolve()
    companyfacts = args.companyfacts_dir.expanduser().resolve()
    statements = args.statements_dir.expanduser().resolve()
    taxonomy = args.taxonomy_dir.expanduser().resolve()
    company_info = args.company_info.expanduser().resolve()
    for path in [companyfacts, statements, taxonomy]:
        if not path.is_dir(): parser.error(f"Input directory missing: {path}")
    if not company_info.is_file(): parser.error("Company information JSON missing")
    assignment = json.loads((repo / "archetypes/sic_to_archetype.json").read_text())
    profiles = args.profiles or list(assignment["archetypes"])
    if set(profiles) - set(assignment["archetypes"]): parser.error("Unknown profile")
    profiles = list(dict.fromkeys(profiles))
    descriptions, sources = load_descriptions(taxonomy)
    print("Reading statement presentation data once...", flush=True)
    rows = load_statement_rows(statements)
    generated = datetime.now(timezone.utc).isoformat()
    summary = {"generated_at": generated, "status": "complete", "profiles": {}}
    with tempfile.TemporaryDirectory(prefix="statement-reviews-") as tmp:
        staging = Path(tmp)
        for profile in profiles:
            config = json.loads((repo / "archetypes" / profile / "profile.json").read_text())
            sics = config["research_scope"]["source_sics"]
            print(f"\n{profile}: source SICs {', '.join(sics)}", flush=True)
            facts, loaded_ciks, selected_count = find_facts_by_sic(sics, companyfacts, company_info)
            facts = add_statement_info(facts, sics, rows, loaded_ciks)
            for fact in facts:
                definition = descriptions.get(fact["fact"])
                fact["description"] = definition["text"] if definition else None
                fact["description_source"] = definition["file"] if definition else None
            grouped = group_facts_by_statement(facts)
            metadata = {"profile_id": profile, "source_sics": sics,
                        "selected_companies": selected_count, "loaded_companies": len(loaded_ciks),
                        "statement_dataset": statements.name, "taxonomy_sources": sources,
                        "generated_at": generated,
                        "company_universe": "Unique CIKs in supplied company-info JSON with matching source SICs",
                        "statement_evidence": "US-GAAP PRE rows in the supplied dataset for successfully loaded company CIKs",
                        "thresholds": {"minimum_appearance": None, "minimum_statement_rate": None}}
            outputs = staging / profile
            outputs.mkdir()
            maps = {statement: collect_mapped(json.loads((repo / relative).read_text())["nodes"])
                    for statement, relative in assignment["archetypes"][profile]["statements"].items()}
            counts = write_review_files(outputs, facts, grouped, metadata, maps)
            summary["profiles"][profile] = {"loaded_companies": len(loaded_ciks), "selected_companies": selected_count, "unique_concepts": len(facts), "statements": counts}
            print(json.dumps(summary["profiles"][profile]), flush=True)
        # Publish generated files only after all requested profiles succeed.
        for profile in profiles:
            target = repo / "review" / profile
            target.mkdir(parents=True, exist_ok=True)
            for path in (staging / profile).iterdir():
                temporary = target / (path.name + ".tmp")
                temporary.write_bytes(path.read_bytes())
                temporary.replace(target / path.name)
            for obsolete in ["bs.md", "is.md", "cf.md", "unclassified.md"]:
                (target / obsolete).unlink(missing_ok=True)
    path = repo / "review/statement_review_summary.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2) + "\n")
    temporary.replace(path)
    print("Created full and unmapped JSON inventories for every requested profile.")


if __name__ == "__main__":
    main()

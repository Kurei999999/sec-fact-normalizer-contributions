"""Validate this repository without SQLite, third-party packages or network access."""

import json
from pathlib import Path
from archetype_validation import validate_archetype
from contract_validation import validate_contract

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    errors = []
    count = 0
    assignment = read(ROOT / "archetypes/sic_to_archetype.json")
    for profile, info in assignment["archetypes"].items():
        try:
            scope_document = read(ROOT / "archetypes" / profile / "profile.json")
            scope = scope_document["research_scope"]
            if scope_document.get("profile_id") != profile:
                errors.append(f"{profile}/profile.json: profile mismatch")
            source_sics = scope["source_sics"]
            if not isinstance(source_sics, list) or not source_sics or any(
                not isinstance(sic, str) or len(sic) != 4
                or not sic.isascii() or not sic.isdigit() for sic in source_sics
            ):
                errors.append(f"{profile}/profile.json: invalid source_sics")
            elif len(source_sics) != len(set(source_sics)):
                errors.append(f"{profile}/profile.json: duplicate source SIC")
            if scope.get("statement_scope") != "profile_level":
                errors.append(f"{profile}/profile.json: unsupported statement scope")
            if not (ROOT / scope["source"]).is_file():
                errors.append(f"{profile}/profile.json: missing source document")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{profile}/profile.json: {exc}")
        for statement, relative in info["statements"].items():
            path = ROOT / relative
            try:
                document = read(path)
                found, _ = validate_archetype(document)
                if (
                    document.get("profile_id") != profile
                    or document.get("statement") != statement
                ):
                    found.append("Profile or statement does not match assignment table")
                errors.extend(f"{relative}: {e}" for e in found)
                count += 1
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{relative}: {exc}")
    for path in sorted((ROOT / "archetypes/api").glob("*.json")):
        try:
            errors.extend(
                f"{path.relative_to(ROOT)}: {e}"
                for e in validate_contract(read(path), path.parent)
            )
            count += 1
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{path.name}: {exc}")
    profiles = assignment["archetypes"]
    sics = set()
    ciks = set()
    for rule in assignment["assignments"]:
        sic = str(rule["sic"]).zfill(4)
        if sic in sics:
            errors.append(f"Duplicate SIC: {sic}")
        sics.add(sic)
        if rule["archetype"] not in profiles:
            errors.append(f'Unknown assignment profile: {rule["archetype"]}')
    for rule in assignment.get("company_overrides", []):
        cik = str(rule["cik"]).zfill(10)
        if cik in ciks:
            errors.append(f"Duplicate company override: {cik}")
        ciks.add(cik)
        if rule["archetype"] not in profiles:
            errors.append(f'Unknown override profile: {rule["archetype"]}')
        if not str(rule.get("reason", "")).strip():
            errors.append(f"Missing override reason: {cik}")
    for name, rule in assignment["defaults"].items():
        if rule["archetype"] not in profiles:
            errors.append(f"Unknown default profile: {name}")
    for error in errors:
        print("ERROR:", error)
    print(f"{count} statement/contract files checked; {len(errors)} errors.")
    print("Structural validation does not establish accounting correctness.")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())

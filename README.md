# Financial fact mappings

Help turn company-reported SEC financial facts into understandable, consistent financial fields.

This repository contains **industry archetypes, concept mappings and normalized field contracts**. You can contribute accounting knowledge without writing code or downloading a financial database.

## Start here

- **File format:** [canonical JSON structure](docs/file_structure.md).
- **Understand the structure:** [normalization explained](docs/how_normalization_works.md).
- **Browse readable maps:** [industry tree index](archetypes/README.md).
- **Try a real example:** [Apple revenue](examples/revenue/explanation.md).
- **Find something to classify:** [simple concept review files](review/README.md).
- **Make a suggestion:** [contribution guide](CONTRIBUTING.md).

## The whole flow

```text
SEC CompanyFacts       SEC Submissions       SEC ticker list
       \                     |                     /
        +--------------------+--------------------+
                             |
                    Import/update raw DB
                             |
                  Company metadata + raw facts
                             |
                  Assign industry archetype
              company override > SIC > default
                             |
                 Map reported concept to node
                             |
                  Resolve normalized API field
              select candidates / calculate / apply signs
                             |
                 Discover and validate periods
             exact periods or compatible YTD subtraction
                             |
              Normalized IS / BS / CF SQLite database
                             |
                    Audit and versioned release
```

Period discovery and fact resolution work together; the diagram explains responsibilities rather than exact function call order.

**This contribution repository covers mappings and their structural validation.** It does not include the private raw database, the complete runtime/exporter or generated SQLite datasets. The source pipeline currently uses `update_daily.py`, `register_archetypes`, then `build_api_db.py`. Contributors can propose useful changes here without running that pipeline.

## Research scope versus runtime assignment

`archetypes/<industry>/profile.json` records the original research SICs from [the research scope document](archetypes/archetype_research_scope.md). Use those SICs to generate development concept inventories. `sic_to_archetype.json` serves a different purpose: it routes companies to available mappings for runtime normalization, including provisional fallbacks. Those fallbacks must not expand an archetype's research population.

The review inventories are generated from these source SICs, independently of runtime assignments. See [the review guide](review/README.md) for the exact snapshot scope and limitations.

## Two separate decisions

```text
Reported concept:
  us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
                |
Industry classification:
  general_corporate / IS
  node: revenue_from_contract_with_customer_excluding_assessed_tax
                |
Normalized output contract:
  revenue
```

Classification says what the concept means. The output contract says which candidate should supply a field and whether calculations are allowed. Adding a concept to a tree does not automatically enable it as the selected API value.

## Repository layout

```text
archetypes/
  sic_to_archetype.json     Industry assignments and company overrides
  <industry>/profile.json  Source SICs used to develop the archetype
  <industry>/is.json       Income-statement classification
  <industry>/bs.json       Balance-sheet classification
  <industry>/cf.json       Cash-flow classification
  <industry>/trees/*.txt   Generated readable classification trees
  archetype_research_scope.md  Research SICs for all archetypes
  api/is.json              Shared output fields and industry source rules
  api/bs.json
  api/cf.json
docs/
  how_normalization_works.md
  normalization.txt        Generated overview of fields and source rules
examples/revenue/          Real input, expected result and explanation
review/<industry>/  Full and unmapped JSON concept inventories
tools/                    Standard-library-only contributor utilities
tests/                    Small offline regression tests
.github/                  Issue/PR templates and automated checks
mapping_snapshot.json     Original export hashes for traceability
```

## For non-coders

1. Open an industry’s unmapped JSON list grouped by BS, IS, CF or unclassified statement from the [review index](review/README.md).
2. Open the original filing and inspect its context.
3. Compare it with the relevant industry text tree.
4. Open a **Classification suggestion** issue using the supplied form.
5. Explain your category, scope and evidence. “Outside primary statements” and “unsure” are valid answers.

A maintainer reviews suggestions before changing mappings or rebuilding a release. No public suggestion writes to a financial database automatically.

## For contributors who edit JSON

Python 3.12+ is required. Basic mapping validation uses the standard library; install `requirements.txt` for the statement-review generator and full test suite.

```bash
python -m pip install -r requirements.txt
python tools/validate_mappings.py
python tools/format_mappings.py
python tools/run_example.py
python -m unittest discover -s tests
```

After changing mappings, regenerate their readable views:

```bash
python tools/generate_trees.py
```

Edit JSON first; `.txt` trees are generated views. See [CONTRIBUTING.md](CONTRIBUTING.md) for review requirements.

## Scope and limitations

- Eight profiles: banks, electric utilities, general corporate, life insurance, oil/gas extraction, personal credit institutions, REITs and savings institutions.
- These are provisional accounting mappings. Passing validation does not prove semantic correctness.
- Do not treat a parent node as an instruction to sum its children. Some children are alternative totals.
- Unmapped concepts may be disclosures that should remain outside primary financial statements.
- Missing values remain NULL; absence is not zero. Never apply absolute value to all cash-flow facts.
- Inventories include all imported concepts for each profile's research SICs, without frequency thresholds. They describe the imported raw snapshot, not complete SEC coverage. See `review/statement_review_summary.json` for population counts.
- `mapping_snapshot.json` records the original exported baseline. Hash differences after edits are expected; it is not an automatically enforced lockfile.
- Contracts include design/review policies. The downstream exporter currently produces candidate previews using period-filing selection and additional runtime quality rules; this small repository does not reproduce all runtime behavior.

Historical references such as `DONE.md` or `data/company_counts_by_sic.json` in assignment metadata describe upstream research inputs and are not required to validate this repository.

## Publication status

No project license or commercial contribution agreement has been selected. The owner should choose and document these before inviting public contributions. This repository does not grant a new open-source license by implication.

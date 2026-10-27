# Concepts needing classification

Choose an industry. The unmapped files preserve the same record format as the full concept inventories, including descriptions, company counts, appearance percentages and statement evidence.

| Industry | All concepts | All by statement | Unmapped concepts | Unmapped by statement |
| --- | --- | --- | --- | --- |
| General corporate | [JSON](general_corporate/facts_by_sic.json) | [JSON](general_corporate/facts_by_statement.json) | [JSON](general_corporate/unmapped_facts_by_sic.json) | [JSON](general_corporate/unmapped_facts_by_statement.json) |
| Banks | [JSON](banks/facts_by_sic.json) | [JSON](banks/facts_by_statement.json) | [JSON](banks/unmapped_facts_by_sic.json) | [JSON](banks/unmapped_facts_by_statement.json) |
| Savings institutions | [JSON](savings_institutions/facts_by_sic.json) | [JSON](savings_institutions/facts_by_statement.json) | [JSON](savings_institutions/unmapped_facts_by_sic.json) | [JSON](savings_institutions/unmapped_facts_by_statement.json) |
| Personal credit institutions | [JSON](personal_credit_institutions/facts_by_sic.json) | [JSON](personal_credit_institutions/facts_by_statement.json) | [JSON](personal_credit_institutions/unmapped_facts_by_sic.json) | [JSON](personal_credit_institutions/unmapped_facts_by_statement.json) |
| Life insurance | [JSON](life_insurance/facts_by_sic.json) | [JSON](life_insurance/facts_by_statement.json) | [JSON](life_insurance/unmapped_facts_by_sic.json) | [JSON](life_insurance/unmapped_facts_by_statement.json) |
| REITs | [JSON](reit/facts_by_sic.json) | [JSON](reit/facts_by_statement.json) | [JSON](reit/unmapped_facts_by_sic.json) | [JSON](reit/unmapped_facts_by_statement.json) |
| Oil and gas extraction | [JSON](oil_and_gas_extraction/facts_by_sic.json) | [JSON](oil_and_gas_extraction/facts_by_statement.json) | [JSON](oil_and_gas_extraction/unmapped_facts_by_sic.json) | [JSON](oil_and_gas_extraction/unmapped_facts_by_statement.json) |
| Electric utilities | [JSON](electric_utilities/facts_by_sic.json) | [JSON](electric_utilities/facts_by_statement.json) | [JSON](electric_utilities/unmapped_facts_by_sic.json) | [JSON](electric_utilities/unmapped_facts_by_statement.json) |

## What to do

Find a concept, read its description and the relevant company filing, then suggest a category through a Classification suggestion issue. “Outside primary statements” and “unsure” are valid answers.

These lists show concepts absent from the corresponding statement map. A concept observed on both IS and CF can appear in both review lists. Unclassified concepts have no observed BS/IS/CF placement and are shown only if absent from all three maps. Non-US-GAAP concepts are retained in the unclassified population; do not assume they belong in the primary statements.

## How the counts work

- Research companies are selected by each profile’s `source_sics` from the supplied company-info JSON, deduplicated by CIK. Runtime fallbacks do not expand the population.
- Company count: number of successfully loaded companies containing the concept, counted once across all their CompanyFacts observations.
- Appearance percentage: company count divided by the number of successfully loaded company files for that archetype. A successfully loaded empty file still belongs to the denominator, matching the original `main.py`.
- Missing or invalid company files are skipped; loaded and selected counts are shown in each file. The company-info snapshot determines the population; this differs from the earlier raw-DB-wide inventory.
- Counts describe concept presence in CompanyFacts, not how many companies reported it on that specific statement.
- No minimum appearance percentage or statement-rate threshold is applied.

## Statement evidence and descriptions

Statement placement comes from the supplied SEC Financial Statement Data Sets `pre.txt` and `sub.txt`, restricted to successfully loaded company CIKs and source SICs. This export uses **2026 Q3** presentation data. Older or unmatched concepts therefore remain unclassified; this does not mean they never appear on a statement.

The presentation pass follows `main.py` and recognizes `us-gaap/` taxonomy versions. Other namespaces are retained without guessed statement placement. Observed statements are evidence for review, not automatic accounting approval. Only BS/IS/CF are primary queues; concepts seen exclusively in EQ, CI or other statement types remain unclassified.

Descriptions use the local US-GAAP 2026 documentation. A missing description is explicitly marked; historical and other-taxonomy definitions may not be present. Original publisher notices apply.

## Regenerate: one script based on main.py

Install generator dependencies once:

```bash
python -m pip install -r requirements.txt
```

Then run from the contribution repository:

```bash
python tools/generate_statement_reviews.py \
  --companyfacts-dir /path/to/companyfacts \
  --company-info /path/to/company_tickers_with_sic.json \
  --statements-dir /path/to/2026q3 \
  --taxonomy-dir /path/to/data/taxonomy/us-gaap/2026
```

Add `--profiles banks` for one archetype. `COMPANYFACTS_PATH` and `SEC_FS_DATA_SETS_PATH` may be supplied through a `.env` file in the working directory instead of the corresponding flags. Never commit that file or private local paths.

The original `main.py` is unchanged. Its copied implementation is `tools/generate_statement_reviews.py`; it reads presentation data once, preserves concepts without thresholds and adds descriptions and mapped/unmapped checks. No raw or normalized DB is opened or modified.

Each `review/<industry>/` folder contains four JSON inventories. `facts_by_sic.json` and `unmapped_facts_by_sic.json` are plain lists. `facts_by_statement.json` and `unmapped_facts_by_statement.json` are dictionaries of BS/IS/CF/unclassified lists. Records retain the same fields when filtered. Generation details and count denominators live separately in `metadata.json`.

`statement_review_summary.json` records populations and review counts. Earlier duplicate inventories and superseded Markdown views have been removed.

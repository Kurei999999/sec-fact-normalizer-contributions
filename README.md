# Financial Fact Normaliser

Companies often report similar financial information under different names. This project maps those facts to consistent fields so they’re easier to compare and use.

## Main goal

We want to normalise as many financial statement facts as possible:

- By industry, using Standard Industrial Classification (SIC) codes.
- By company, where industry mappings need more detail.

The aim is to keep as much useful information as possible and make the mappings available for everyone to inspect and improve.

## What can you get?

A free bulk financial database built using this normaliser, available through the project’s [download website](https://kurei999999.github.io/sec-fact-normalizer-contributions/).

The database improves as the mappings improve. More correctly mapped facts mean better coverage and more reliable data—so contributions directly help everyone using it.

The raw financial data comes from the SEC API. Terms for redistribution, commercial use, personal use and research still need to be finalised.

See the [website documentation](website/README.md) for download and publishing details.

## How does it work?

### `archetypes/`

This is where the industry mappings live. They organise reported facts into income statements, balance sheets and cash flow statements.

Companies are assigned an industry mapping using their SIC code, with company-specific overrides where needed.

[Browse the industry mappings](archetypes/README.md).

### `archetypes/api/`

These mappings define the common fields used in the downloadable database. They connect industry concepts to fields such as `revenue`, `operatingIncome` and `netIncome`.

For example, run this SQL against the downloaded database to get Apple’s latest available annual income statement:

```sql
SELECT i.*
FROM income_statements AS i
JOIN companies AS c ON c.cik = i.cik
WHERE c.ticker = 'AAPL'
  AND i.frequency = 'annual'
  AND i.period = 'FY'
ORDER BY i.date DESC, i.reportedCurrency
LIMIT 1;
```

Result from the current database snapshot, shown as JSON:

```json
{
  "cik": "0000320193",
  "date": "2025-09-27",
  "startDate": "2024-09-29",
  "fiscalYear": "2025",
  "period": "FY",
  "frequency": "annual",
  "reportedCurrency": "USD",
  "anchorFilingDate": "2025-10-31",
  "anchorAccession": "0000320193-25-000079",
  "revenue": "416161000000",
  "costOfRevenue": "220960000000",
  "grossProfit": "195201000000",
  "researchAndDevelopmentExpenses": "34550000000",
  "generalAndAdministrativeExpenses": "8077000000",
  "sellingAndMarketingExpenses": "19524000000",
  "sellingGeneralAndAdministrativeExpenses": "27601000000",
  "otherExpenses": null,
  "operatingExpenses": "62151000000",
  "costAndExpenses": "283111000000",
  "netInterestIncome": null,
  "interestIncome": null,
  "interestExpense": null,
  "depreciationAndAmortization": "11698000000",
  "ebitda": null,
  "ebit": null,
  "nonOperatingIncomeExcludingInterest": null,
  "operatingIncome": "133050000000",
  "totalOtherIncomeExpensesNet": "-321000000",
  "incomeBeforeTax": "132729000000",
  "incomeTaxExpense": "20719000000",
  "netIncomeFromContinuingOperations": null,
  "netIncomeFromDiscontinuedOperations": null,
  "otherAdjustmentsToNetIncome": null,
  "netIncome": "112010000000",
  "netIncomeDeductions": null,
  "bottomLineNetIncome": null,
  "eps": "7.49",
  "epsDiluted": "7.46",
  "weightedAverageShsOut": "14948500000",
  "weightedAverageShsOutDil": "15004697000"
}
```

Financial values are stored as decimal strings to preserve precision. Monetary amounts are in the reported currency, EPS is currency per share, and weighted-average share fields are share counts. `null` means no value is available for that field; it does not mean zero.

### `trees/`

Each industry has readable text trees showing how its facts are organised. These let you browse the mapping structure without digging through JSON.

Edit the source JSON when proposing changes; the text trees are generated from it.

### `review/`

This directory contains the reported concepts found in the data, including those already mapped and those still waiting for review.

You can see their descriptions, how many companies use them and evidence of where they appear in financial statements.

[Find facts to review](review/README.md).

## Want to contribute?

You don’t need to write code to help.

### If you code

You can add missing mappings, fix existing ones or improve the tools.

See the [contribution guide](CONTRIBUTING.md) for setup and validation instructions, and the [file format documentation](docs/file_structure.md) for the mapping structure.

### If you don’t code

Browse the [unmapped facts](review/README.md) and open a **Classification suggestion** issue if you recognise a concept or spot something that looks wrong.

Include the concept name, your suggested classification and a link to a company filing if possible. You don’t need to have the full answer—questions and examples help too.

## A work in progress

The mappings still need review, and coverage is incomplete. Some facts belong in disclosures rather than the main financial statements, so not every unmapped fact needs to be added.

The review lists reflect the data imported so far, rather than everything available from the SEC.

This repository contains mappings and contributor tools. The full database generation pipeline and database files are maintained separately.

A project licence and contribution terms have not yet been selected. This repository does not grant an open-source licence by implication.

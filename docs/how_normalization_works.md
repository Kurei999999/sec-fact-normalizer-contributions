# How normalization works

A fact is an observation reported by a company: a concept, value, unit, period and filing. “Revenue” is the common output field we want users to understand. These are not always named the same way.

## 1. Choose the company's industry structure

A bank and a manufacturer may report different statements. The assignment table chooses an archetype using a company override first, then SIC, then a default. An assignment is a working classification, not proof that every accounting rule fits the company.

## 2. Classify the reported concept

The industry tree puts concepts into meaningful nodes. Several reported alternatives may sit beneath one broad heading. A parent-child relationship is presentation; it does not automatically mean addition.

An uncategorized concept is one absent from all three IS/BS/CF maps for the selected profile in this sample. Its statement is deliberately unknown. An instant observation is not enough to prove it belongs on the primary balance sheet.

## 3. Resolve a normalized field

The API contracts define stable names such as `revenue`, `totalAssets` and `operatingCashFlow`. Industry rules describe reported candidates, source selection, formulas, signs and conditions. A valid mapping may still produce no eligible value for a particular filing.

“Proposed” and “review” are metadata used by the rules. They are not an assertion that an accountant approved the mapping. See each contract for its exact policy; runtime preview behavior is separate.

## 4. Keep periods and amounts compatible

A fiscal-year label may differ from the calendar year. Quarters must have compatible boundaries. Q2 standalone cash flow may be six-month YTD minus Q1 YTD, but only with compatible inputs. EPS, ratios and weighted-average shares must not be subtracted that way.

## 5. Preserve source evidence

The source database retains reported values. Normalization may select another reported candidate or apply a reviewed transformation. RGA's observed source sign anomaly, for example, requires a correction pinned to the exact company, concept, period and original value. An industry-wide positive-sign rule would be wrong.

Only a maintainer-approved downstream change reaches a later dataset release. Public suggestions do not update source facts or output databases directly.

## What a contributor decides

You can answer: “What does this concept mean, and where should it belong?” Supply a filing link and explain scope. You do not need to implement the exporter.

See `normalization.txt` for the generated contract overview and [archetype trees](../archetypes/README.md) for industry structure.

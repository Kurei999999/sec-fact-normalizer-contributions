# Apple revenue: one complete mapping example

Apple's FY2025 observation runs from 2024-09-29 to 2025-09-27. The reported concept is `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`, with value `416161000000` USD. Its filing accession and original filing link are included in `raw_facts.json`.

Follow the steps:

1. The company uses the `general_corporate` profile.
2. In `archetypes/general_corporate/is.json`, find the concept. It belongs to node `revenue_from_contract_with_customer_excluding_assessed_tax`.
3. In `archetypes/api/is.json`, find field `revenue` and its `general_corporate` direct rules. The concept and node are referenced there.
4. For this explicitly chosen single observation, the demonstration passes the amount through unchanged as the candidate revenue value.

Run `python tools/run_example.py`. It verifies the mapping and expected result using only the included JSON files.

This is a teaching example, not a replacement resolver. It does not compare competing values, approve accounting conditions, derive quarters or reproduce all production quality guards. `expected.json` records this one expected demonstration result.

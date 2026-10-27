# Archetype research scope

This document records the SIC populations originally used to develop each archetype. It is a readable transcription of the original project research notes (`DONE.md`).

| Archetype                      | Source SICs                                                            |
| ------------------------------ | ---------------------------------------------------------------------- |
| `general_corporate`            | `2834`, `2836`, `7372`, `3674`, `3571`, `5311`, `5961`, `3569`, `7389` |
| `banks`                        | `6021`, `6022`, `6029`                                                 |
| `savings_institutions`         | `6035`, `6036`                                                         |
| `personal_credit_institutions` | `6141`                                                                 |
| `life_insurance`               | `6311`                                                                 |
| `reit`                         | `6798`                                                                 |
| `oil_and_gas_extraction`       | `1311`                                                                 |
| `electric_utilities`           | `4911`                                                                 |

## How to use this scope

- Each archetype's `profile.json` is the machine-readable configuration; keep it consistent with this table.
- Generate research concept inventories from companies whose reported SIC is in `research_scope.source_sics`.
- Do not expand research inventories using runtime fallbacks or company overrides in `sic_to_archetype.json`.
- Keep all observed concepts, including rare concepts and concepts without a statement classification. Occurrence counts help prioritize review rather than exclude concepts.
- These are profile-level research populations. The original notes did not document different IS/BS/CF source populations; this table does not establish statement-level coverage.
- Changing the scope requires updating the table, the corresponding profile metadata, and regenerated review inventories.

## Separate from runtime assignments

A company may use an archetype provisionally for normalization without belonging to the research population used to develop it. Runtime assignment and research scope serve different purposes. Neither SIC membership nor occurrence frequency proves accounting equivalence.

# Contributing

You do not need to code. An explanation backed by a filing is a useful contribution.

## Suggest a classification

Open a Classification suggestion issue with:

- Industry profile and exact concept name (a review item ID is optional).
- Company CIK (ticker optional), industry and reported concept.
- Filing URL and accession, exact period, unit and value.
- Proposed statement and category, or “outside primary statements / unsure”.
- Scope: one observation, this company, or an industry.
- Why the concept represents that category, using nearby filing lines when helpful.

Labels alone are not enough. A consolidated total, a segment subtotal and a geographic breakdown may share similar labels. Prefer links and short descriptions to copying entire filings.

## Edit a mapping

Read [the file structure guide](docs/file_structure.md) first. Run `python tools/format_mappings.py` to check formatting; `--write` applies the canonical layout.

1. Start with the industry JSON under `archetypes/<industry>/`.
2. Keep one concept assigned to one node within a statement. Never remove an existing concept silently to make a test pass.
3. If changing output selection, edit the corresponding contract under `archetypes/api/` too. A classification change alone does not create a new API source rule.
4. Explain competing concepts, priority, scope, signs, calculations and missing-data behavior.
5. Add a small reproducible example when behavior changes. Never add a full database or credentials.
6. Run validation, the example and tests, then regenerate text trees.
7. Open a PR using the template. Maintainers check accounting evidence and downstream impact before accepting it.

Use a company-specific proposal when industry-wide equivalence is unproven. A source sign/scale error is a precisely scoped correction request, not a reason to change an entire industry's sign convention.

## Maintainer handoff

This repository starts as a snapshot of the upstream mappings. Accepted edits do not synchronize to the commercial pipeline automatically. Maintainers must bring the accepted JSON changes into the pipeline, register the updated archetypes, rebuild a new output DB and audit affected companies before releasing it. Keep the original export manifest as baseline provenance; document later releases separately. Refresh the research review inventories when mappings make entries obsolete.

## Contributions we need

- Classifications for uncategorized concepts.
- Evidence that two apparent alternatives have different accounting scope.
- Missing mappings and better explanations of field definitions.
- Reproducible error reports for dates, signs and source selection.

The per-industry queues cover uncategorized concepts only. A mapped concept whose API field is still NULL is a separate resolver issue; report it with the same filing evidence.

## Review states

Suggested -> needs evidence -> under review -> accepted or declined.
Acceptance is followed by a mapping update and a later downstream dataset release. It does not directly modify a published database.

## Commercial use and licensing

The project owner has not yet selected a project license or contribution terms. Before this repository is opened for external contributions, those terms must state how accepted work may be used in the commercial dataset. Do not infer any contributor license agreement from this document.

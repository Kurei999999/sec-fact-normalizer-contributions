# Archetype file structure

## Two file families

Industry statements classify concepts. API contracts resolve shared output fields. They deliberately use different schemas because they do different jobs.

| Files                                       | Purpose                                    | Schema version          |
| ------------------------------------------- | ------------------------------------------ | ----------------------- |
| `<industry>/is.json`, `bs.json`, `cf.json`  | Industry concept classification trees      | `1.4.0`                 |
| `api/is.json`, `api/bs.json`, `api/cf.json` | Source selection and calculation contracts | `0.2.0`                 |
| `sic_to_archetype.json`                     | Industry assignment configuration          | Its own existing schema |

Different industries may have different hierarchies and accounting categories. A common format does not mean identical accounting rules.

## Industry statement envelope

Every industry statement has the following keys, in this order:

```text
schema_version         string; 1.4.0
profile_id             string; industry identifier
statement              IS, BS or CF
status                 string; existing review/draft status
validation_profile     string; additional validation behavior
description            string; purpose and scope
mapping_rules          object; existing interpretation constraints
classification_notes   array; shared explanatory notes
metadata_contract      object; metadata interpretation notes
taxonomy_reference     object; taxonomy bibliography
sources                array; source records
metadata_notes         object; additional metadata explanation
nodes                  array; actual classification tree
unmapped_placeholders  array; proposed categories without a source mapping
```

All keys are present even when optional content is empty. Use `[]` for empty arrays and `{}` for empty metadata objects. Empty metadata means not supplied; do not invent a source or taxonomy claim.

Former `source_reference` and `presentation_reference` objects are preserved as entries in `sources`:

```json
{
  "role": "source_reference",
  "details": {
    "concept_source": "User-supplied unique concepts list"
  }
}
```

Source records may retain their existing role-specific keys. Metadata dictionaries retain their existing contents; the standard defines their container, not a universal set of accounting notes.

## Nodes

Every node has the same keys in the same order:

```json
{
  "node_id": "cash_and_cash_equivalents",
  "metric_id": "cash_and_cash_equivalents",
  "label": "Cash and cash equivalents",
  "node_kind": "line_item",
  "aggregation_policy": "none",
  "period_type": "instant",
  "unit_type": "monetary",
  "contra": false,
  "taxonomy_type": null,
  "classification_note": "",
  "concepts": [
    {
      "name": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
      "status": "proposed",
      "review_reason": null
    }
  ],
  "children": []
}
```

- `node_id`: nonempty identifier, unique within the mapped tree.
- `label`: nonempty human-readable label.
- `node_kind`: `group`, `total` or `line_item` in the mapped tree. `total` also covers subtotal presentation.
- `group`: `metric_id`, `period_type`, `unit_type`, `contra` and `taxonomy_type` are null; `concepts` is empty. Groups describe structure rather than facts.
- `total` and `line_item`: `metric_id` equals `node_id`; at least one concept is required in the mapped tree.
- `line_item`: a leaf. It still includes `children: []` for a consistent shape.
- `total`: may have children. That does not authorize summing them.
- `period_type`: `instant` or `duration` for mapped fact nodes.
- `unit_type`: `monetary`, `shares`, `per_share`, `percent` or `ratio` for mapped fact nodes.
- `contra`: boolean for mapped fact nodes. It does not instruct the resolver to negate a source value.
- `taxonomy_type`: existing taxonomy type string, or null when not supplied. Never infer one merely to fill the field.
- `classification_note`: text; use an empty string when no node-specific note exists.
- `aggregation_policy`: always `none`. Hierarchy does not prescribe arithmetic.

Concept objects always contain `name`, `status`, `review_reason` in that order. Status is `proposed` or `review`. A review concept requires a nonempty reason; otherwise the reason may be null. Each concept occurs once per statement tree.

## Unmapped placeholders

These use the same node keys but live only in `unmapped_placeholders`, outside the mapped tree. They may lack fact metadata and concepts. Legacy `analytical` placeholders are retained here only; they are not supported as mapped node kinds.

Placeholders do not create source mappings, approved calculations, zero values or output field coverage. Null metadata means unknown or not applicable. It must be reviewed before moving a placeholder into `nodes` as a mapped fact.

## API contract layout

The API contract envelope uses this order:

```text
schema_version
profile_id
statement
status
schema_kind
description
source_profiles
metadata_fields
resolution_policy
rule_contract
metrics
open_decisions
```

Each metric defines an output field and per-industry source mappings. Direct rules identify concepts/nodes; calculation rules retain their existing expressions, inputs and conditions. Contracts are not converted into node trees. Rule lists, priorities, formulas, signs and review conditions retain their existing values and order.

The format standard does not override the full API contract validator. Use that validator for method-specific rule requirements.

## Encoding and changes

Use UTF-8, two-space indentation and one final newline. Preserve list order: classification trees and source rules can carry presentation or selection meaning. The formatter never sorts concept, node or rule lists. `mapping_rules` object keys are alphabetized; their values are preserved.

The 1.4.0 migration adds explicit empty/null fields, unifies the envelope and moves legacy bibliography into `sources`. It retains all node IDs, concept assignments, review reasons, fact metadata, hierarchy, and interpretation rules. It does not approve accounting semantics.

Changed JSON produces new definition hashes and registered versions on the next explicit registration. Existing registered DB snapshots are not updated automatically. Finish or resume an in-progress export with its existing registered definitions before registering a new version.

## Contributor commands

In the contribution repository:

```bash
python tools/validate_mappings.py
python tools/format_mappings.py
python tools/format_mappings.py --write  # only when formatting changes are wanted
python tools/generate_trees.py
python -m unittest discover -s tests
```

In the main pipeline repository, `validate_archetype.py <path>` also checks the 1.4.0 layout. The shared implementation is `new_db/validation/archetype_format.py`; the standalone contribution copy is `tools/archetype_format.py`.

## Archetype research scope (`profile.json`)

Each industry directory includes one `profile.json`, shared by its IS/BS/CF definitions:

```json
{
  "schema_version": "1.0.0",
  "profile_id": "electric_utilities",
  "research_scope": {
    "source_sics": ["4911"],
    "description": "SIC population used to develop this archetype and generate its research concept inventory. This does not define runtime company assignments.",
    "source": "archetypes/archetype_research_scope.md",
    "statement_scope": "profile_level"
  }
}
```

`source_sics` contains unique four-digit SIC strings from the original research scope documented in `archetypes/archetype_research_scope.md`. Select companies by their source SIC when generating the research inventory. Do not expand this population using runtime fallbacks or company overrides in `sic_to_archetype.json`.

`statement_scope: profile_level` records the scope supplied by `archetypes/archetype_research_scope.md`, which does not document separate IS/BS/CF populations. It does not assert independent statement-level coverage. If later evidence establishes different source populations by statement, introduce an explicit statement-level scope rather than assuming one.

This metadata is not read by the current financial exporter and does not change registered industry assignments.

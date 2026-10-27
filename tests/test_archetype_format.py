import unittest
from copy import deepcopy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from archetype_format import canonical_statement, validate_format


class FormatTests(unittest.TestCase):
    def sample(self):
        return dict(
            schema_version="1.0.0",
            profile_id="test",
            statement="IS",
            status="draft",
            description="Example",
            mapping_rules={"children_imply_arithmetic": False},
            source_reference={"concept_count": 1},
            nodes=[
                dict(
                    node_id="revenue",
                    metric_id="revenue",
                    label="Revenue",
                    node_kind="line_item",
                    aggregation_policy="none",
                    period_type="duration",
                    unit_type="monetary",
                    contra=False,
                    concepts=[dict(name="us-gaap:Revenues", status="proposed")],
                )
            ],
        )

    def test_idempotent_preserves_mapping_and_source_notes(self):
        old = self.sample()
        saved = deepcopy(old)
        new = canonical_statement(old)
        self.assertEqual(old, saved)
        self.assertEqual(new, canonical_statement(new))
        self.assertEqual(new["nodes"][0]["concepts"][0]["name"], "us-gaap:Revenues")
        self.assertEqual(
            new["sources"],
            [{"role": "source_reference", "details": {"concept_count": 1}}],
        )
        self.assertEqual(validate_format(new), [])

    def test_unknown_fields_are_not_silently_dropped(self):
        old = self.sample()
        old["nodes"][0]["unexpected_accounting_rule"] = True
        with self.assertRaises(ValueError):
            canonical_statement(old)

    def test_mapped_missing_metadata_is_rejected(self):
        new = canonical_statement(self.sample())
        new["nodes"][0]["period_type"] = None
        self.assertTrue(any("period_type" in e for e in validate_format(new)))

    def test_placeholders_do_not_create_mapped_facts(self):
        old = self.sample()
        old["unmapped_placeholders"] = [
            dict(
                node_id="unknown",
                metric_id="unknown",
                label="Unknown",
                node_kind="line_item",
                aggregation_policy="none",
                concepts=[],
            )
        ]
        new = canonical_statement(old)
        self.assertEqual(validate_format(new), [])
        new["nodes"].append(new["unmapped_placeholders"][0])
        new["unmapped_placeholders"] = []
        self.assertTrue(any("no concepts" in e for e in validate_format(new)))


if __name__ == "__main__":
    unittest.main()

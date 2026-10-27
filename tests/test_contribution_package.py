import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from archetype_validation import validate_archetype
from contract_validation import validate_contract
from run_example import run_example


class ContributionTests(unittest.TestCase):
    def test_real_example(self):
        self.assertEqual(run_example()["value"], "416161000000")

    def test_duplicate_concept_is_rejected(self):
        document = json.loads(
            (ROOT / "archetypes/general_corporate/is.json").read_text()
        )

        def walk(nodes):
            for node in nodes:
                yield node
                yield from walk(node.get("children", []))

        node = next(n for n in walk(document["nodes"]) if n.get("concepts"))
        node["concepts"].append(copy.deepcopy(node["concepts"][0]))
        errors, _ = validate_archetype(document)
        self.assertTrue(any("duplicate concept" in e for e in errors))

    def test_unknown_api_node_is_rejected(self):
        path = ROOT / "archetypes/api/is.json"
        document = json.loads(path.read_text())
        rule = next(
            r
            for m in document["metrics"]
            for mapping in m["source_mappings"].values()
            for r in mapping["rules"]
            if r.get("node_id")
        )
        rule["node_id"] = "this_node_does_not_exist"
        self.assertTrue(validate_contract(document, path.parent))

    def test_queue_preserves_source_context(self):
        summary = json.loads((ROOT / "review/statement_review_summary.json").read_text())
        self.assertEqual(summary["status"], "complete")
        for profile, counts in summary["profiles"].items():
            directory = ROOT / "review" / profile
            metadata = json.loads((directory / "metadata.json").read_text())
            queue = json.loads((directory / "unmapped_facts_by_statement.json").read_text())
            full = json.loads((directory / "facts_by_statement.json").read_text())
            self.assertEqual(metadata["loaded_companies"], counts["loaded_companies"])
            for statement, items in queue.items():
                originals = {item["fact"]: item for item in full[statement]}
                self.assertEqual(len(items), counts["statements"][statement]["unmapped"])
                self.assertEqual(len({i["fact"] for i in items}), len(items))
                for item in items:
                    self.assertEqual(item, originals[item["fact"]])
                    self.assertGreater(item["company_count"], 0)
                    self.assertEqual(item["appearance_percentage"], round(item["company_count"] / metadata["loaded_companies"] * 100, 2))


if __name__ == "__main__":
    unittest.main()

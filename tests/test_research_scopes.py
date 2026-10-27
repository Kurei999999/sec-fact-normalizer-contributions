"""Research populations match the readable scope table, not runtime fallbacks."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "archetypes/archetype_research_scope.md"


class ResearchScopesTests(unittest.TestCase):
    def test_scopes_exactly_match_documented_research_sics(self):
        expected = {}
        for line in (ROOT / SOURCE).read_text().splitlines():
            match = re.fullmatch(r"\|\s*`([a-z_]+)`\s*\|\s*(.+?)\s*\|", line)
            if match:
                expected[match[1]] = re.findall(r"`(\d{4})`", match[2])
        assignment = json.loads((ROOT / "archetypes/sic_to_archetype.json").read_text())
        self.assertEqual(set(expected), set(assignment["archetypes"]))
        for profile, sics in expected.items():
            document = json.loads(
                (ROOT / "archetypes" / profile / "profile.json").read_text()
            )
            self.assertTrue(sics)
            self.assertEqual(document["profile_id"], profile)
            self.assertEqual(document["research_scope"]["source_sics"], sics)
            self.assertEqual(document["research_scope"]["source"], SOURCE)


if __name__ == "__main__":
    unittest.main()

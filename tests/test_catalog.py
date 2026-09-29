import json
import unittest
from pathlib import Path

from harmness.catalog import CatalogError, compile_harm, load_catalog

ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def test_builtin_catalog_loads_and_blocks_by_severity(self):
        harms = load_catalog()
        self.assertGreaterEqual(len(harms), 1)
        self.assertEqual(len(harms), len({harm.id for harm in harms}))
        for harm in harms:
            if harm.severity in {"critical", "high"}:
                self.assertTrue(harm.blocks_solution, harm.id)
            else:
                self.assertFalse(harm.blocks_solution, harm.id)

    def test_listable_fields_are_present(self):
        harm = load_catalog()[0]
        self.assertTrue(harm.title)
        self.assertTrue(harm.description)
        self.assertTrue(harm.category)
        self.assertIn("match", harm.rule)

    def test_invalid_rule_is_rejected(self):
        with self.assertRaises(CatalogError):
            compile_harm(
                {
                    "id": "broken-rule",
                    "title": "Broken",
                    "severity": "low",
                    "category": "test",
                    "description": "A rule that cannot compile.",
                    "blocks_solution": False,
                    "rule": {"match": "("},
                }
            )

    def test_catalog_file_is_stored_with_the_package(self):
        self.assertTrue((ROOT / "src" / "harmness" / "harms.json").is_file())
        raw = json.loads((ROOT / "src" / "harmness" / "harms.json").read_text(encoding="utf-8"))
        self.assertEqual([harm["id"] for harm in raw["harms"]], [harm.id for harm in load_catalog()])


if __name__ == "__main__":
    unittest.main()

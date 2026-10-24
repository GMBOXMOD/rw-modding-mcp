#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""节感知查键、有界搜索和定向速查回归；不依赖反编译产物。"""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rw_lint
from rw_mcp import dataset, impl

UNIT_KEYS = ["name", "price", "maxHp", "mass", "radius", "image", "movementType", "canAttack",
             "canAttackFlyingUnits", "canAttackLandUnits", "canAttackUnderwaterUnits",
             "maxAttackRange", "shootDelay", "projectile", "directDamage", "life", "speed"]


def chars(value):
    return len(json.dumps(value, ensure_ascii=False))


class LookupTests(unittest.TestCase):
    def test_default_brief_and_explicit_full(self):
        brief = impl.lookup_key("isVisible")
        full = impl.lookup_key("isVisible", detail="full")
        self.assertTrue(brief["ok"])
        self.assertEqual(brief["detail"], "brief")
        self.assertNotIn("csv", brief)
        self.assertNotIn("cn", brief)
        self.assertLessEqual(len(brief["entries"]), 3)
        self.assertGreater(brief["entries_omitted"], 0)
        self.assertGreaterEqual(len(full["cn"]), 4)
        self.assertTrue(full["csv"])
        self.assertLess(chars(brief), chars(full))

    def test_long_examples_are_omitted_instead_of_cut_in_half(self):
        raw = {"found": True, "cn": [{"chapter": "M", "line": 1,
               "description": "x" * 400, "correct_examples": ["setUnitMemory: " + "x=1," * 100]}],
               "csv": [], "constraints": ["important limit"], "conflicts": [], "warnings": []}
        result = impl._brief_key(raw)
        entry = result["entries"][0]
        self.assertEqual(entry["example"], "")
        self.assertTrue(entry["example_omitted"])
        self.assertTrue(entry["truncated"])
        self.assertEqual(len(entry["description"]), 200)
        self.assertEqual(result["constraints"], ["important limit"])

    def test_section_filters_both_tables(self):
        result = impl.lookup_key("isVisible", section="[action_button]", detail="full")
        self.assertTrue(result["section_match"])
        self.assertEqual({r["chapter"] for r in result["cn"]}, {"M"})
        self.assertEqual({rw_lint.section_family(r["section"]) for r in result["csv"]}, {"M"})
        self.assertEqual([r["letter"] for r in result["sections"]], ["M"])
        self.assertNotIn("1.15p9", result["versions"])
        self.assertTrue(result["constraints"])

    def test_section_aliases_and_disambiguated_rules(self):
        for section in ("action", "M", "hiddenAction_hidden"):
            r = impl.lookup_key("isVisible", section=section)
            self.assertTrue(r["section_match"])
            self.assertTrue(any("静态 false" in note for note in r["notes"]))
        turret = impl.lookup_key("canAttack", section="turret_main")
        self.assertFalse(any("三个目标类型" in note for note in turret.get("notes", [])))
        decal = impl.lookup_key("isVisible", section="decal_picture")
        self.assertEqual(decal["versions"], ["1.15p9"])
        self.assertFalse(any("hiddenAction" in note for note in decal.get("notes", [])))

    def test_unconfirmed_section_is_not_presented_as_supported(self):
        r = impl.lookup_key("canAttack", section="movement")
        self.assertTrue(r["found"])
        self.assertFalse(r["section_match"])
        self.assertEqual(r["agreement"], "section_unconfirmed")
        self.assertEqual(r["entries"], [])
        self.assertTrue(r["available_sections"])
        self.assertTrue(r["warnings"])

    def test_conflicts_and_constraints_survive_brief_mode(self):
        for key in ("energyNeedstoRechargeToFull", "name", "isVisible", "alwaysSinglePress"):
            with self.subTest(key=key):
                full = impl.lookup_key(key, detail="full")
                brief = impl.lookup_key(key)
                self.assertEqual(brief["conflicts"], full["conflicts"])
                self.assertEqual(brief["warnings"], full["warnings"])
                self.assertEqual(brief.get("constraints", []), full["constraints"])
                for note in full["notes"]:
                    self.assertIn(note, brief.get("notes", []))

    def test_batch_deduplicates_and_passes_query_options(self):
        r = impl.lookup_key(keys=["isVisible", "isVisible", "isActive"], section="action", detail="full")
        self.assertEqual(r["requested_count"], 3)
        self.assertEqual(r["count"], 2)
        self.assertEqual(r["found"], 2)
        self.assertEqual(r["results"]["isVisible"], impl.lookup_key("isVisible", section="action", detail="full"))

    def test_legacy_positional_arguments_and_suggestions(self):
        r = impl.lookup_key("canAtack", 2)
        self.assertTrue(r["ok"])
        self.assertFalse(r["found"])
        self.assertLessEqual(len(r["suggestions"]), 2)
        self.assertTrue(impl.lookup_key("canattack", 5, None)["found"])

    def test_bad_query_options_do_not_throw(self):
        for args in ({"detail": "invalid"}, {"section": "nonesuch"}, {"keys": []},
                     {"keys": [str(n) for n in range(33)]}, {"keys": [None]}):
            with self.subTest(args=args):
                self.assertFalse(impl.lookup_key("canAttack", **args)["ok"])

    def test_common_unit_batch_size(self):
        brief = impl.lookup_key(keys=UNIT_KEYS)
        full = impl.lookup_key(keys=UNIT_KEYS, detail="full")
        self.assertTrue(brief["ok"])
        self.assertLess(chars(brief), chars(full) * 0.55)
        self.assertLess(chars(brief), 15000)

    def test_csv_heading_metadata_and_dedup_are_section_aware(self):
        rows = [
            ["", "Section", "", "[core]", ""],
            ["", "isVisible", "boolean", "same", "example"],
            ["", "Section", "", "[graphics]", ""],
            ["", "isVisible", "boolean", "same", "example"],
            ["", "", "", "[action_just_an_example]", ""],
            ["", "image", "file", "picture", "image.png"],
            ["[attack]", "canAttack: true", "boolean", "attack", ""],
        ]
        with tempfile.TemporaryDirectory(prefix="rw-query-") as d:
            self.assertEqual(Path(d).resolve().parent, Path(tempfile.gettempdir()).resolve())
            p = Path(d) / "ref.csv"
            with p.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows(rows)
            data = rw_lint.load_csv_rows(str(p))
            self.assertEqual([r["section"] for r in data["isvisible"]], ["core", "graphics"])
            self.assertEqual(data["image"][0]["section"], "graphics")
            self.assertEqual(data["canattack"][0]["section"], "attack")


class SourceSearchTests(unittest.TestCase):
    def setUp(self):
        self.rows = [("custom/A.java", i + 1, line) for i, line in enumerate([
            "start", "alpha", "alpha beta", "beta", "%{value}", "end"])]
        self.rows += [("custom/B.java", 1, "ALPHA"), ("other/C.java", 1, "nothing")]
        patched = patch.object(dataset, "get_java_lines", return_value=self.rows)
        patched.start()
        self.addCleanup(patched.stop)

    def test_legacy_regex_and_new_modes(self):
        old = impl.search_source("alpha|beta", True, False, "custom/A", 50)
        new = impl.search_source("alpha|beta", mode="regex", path_filter="custom/A")
        self.assertEqual(old["total_matches"], 3)
        self.assertEqual(new["total_matches"], old["total_matches"])
        literal = impl.search_source("alpha|beta")
        self.assertEqual(literal["total_matches"], 0)
        self.assertTrue(literal["hints"])
        self.assertFalse(impl.search_source("alpha", regex=True, mode="literal")["ok"])

    def test_literal_escape_hint_does_not_change_query(self):
        r = impl.search_source(r"%\{", regex=False)
        self.assertEqual(r["total_matches"], 0)
        self.assertEqual(r["mode"], "literal")
        self.assertTrue(any("不要写" in hint for hint in r["hints"]))
        self.assertEqual(impl.search_source("%{")["total_matches"], 1)

    def test_context_does_not_cross_file_boundaries(self):
        r = impl.search_source("end", context_lines=2)
        self.assertEqual(r["matches"][0]["before"], ["beta", "%{value}"])
        self.assertEqual(r["matches"][0]["after"], [])
        self.assertNotIn("before", impl.search_source("end", context_lines=0)["matches"][0])

    def test_batch_returns_one_match_per_line_and_pattern_counts(self):
        r = impl.search_source(patterns=["alpha", "beta", "alpha"])
        self.assertEqual(r["total_matches"], 4)
        self.assertEqual(r["by_pattern"], {"alpha": 3, "beta": 2})
        combined = next(m for m in r["matches"] if m["text"] == "alpha beta")
        self.assertEqual(combined["patterns"], ["alpha", "beta"])

    def test_empty_reasons_are_distinct(self):
        self.assertEqual(impl.search_source("missing")["reason"], "no_match")
        self.assertEqual(impl.search_source("alpha", path_filter="bad/path")["reason"], "path_filter_no_files")
        with patch.object(dataset, "get_java_lines", return_value=[]):
            self.assertEqual(impl.search_source("alpha")["reason"], "source_unavailable")

    def test_case_sensitive_and_windows_path_filters(self):
        r = impl.search_source("ALPHA", case_sensitive=True, path_filter=r"custom\B.java")
        self.assertEqual(r["total_matches"], 1)
        self.assertEqual(r["files_scanned"], 1)

    def test_result_pagination_has_no_skips_or_duplicates(self):
        offset, seen = 0, []
        while True:
            r = impl.search_source("alpha", max_results=1, offset=offset)
            seen.extend((m["file"], m["line"]) for m in r["matches"])
            if r["next_offset"] is None:
                break
            self.assertGreater(r["next_offset"], offset)
            offset = r["next_offset"]
        self.assertEqual(len(seen), 3)
        self.assertEqual(len(set(seen)), 3)
        self.assertFalse(impl.search_source("alpha", offset=99)["truncated"])

    def test_character_budget_and_long_lines(self):
        rows = [("large.java", n, "alpha " + "x" * 2000) for n in range(1, 21)]
        with patch.object(dataset, "get_java_lines", return_value=rows):
            seen, offset = [], 0
            for _ in range(25):
                r = impl.search_source("alpha", max_results=200, context_lines=5, max_chars=1000, offset=offset)
                self.assertLessEqual(r["content_chars"], 1000)
                self.assertEqual(r["content_chars"], len(json.dumps(r["matches"], ensure_ascii=False, separators=(",", ":"))))
                self.assertTrue(r["matches"])
                self.assertTrue(r["matches"][0]["text_truncated"])
                seen.extend(m["line"] for m in r["matches"])
                if r["next_offset"] is None:
                    break
                offset = r["next_offset"]
            self.assertEqual(seen, list(range(1, 21)))

    def test_invalid_options_return_errors(self):
        for kwargs in ({"pattern": "(" , "mode": "regex"}, {"pattern": "x", "mode": "glob"},
                       {"patterns": []}, {"patterns": ["a"] * 2 + [None]},
                       {"patterns": [str(n) for n in range(9)]}, {"pattern": "a" * 201}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(impl.search_source(**kwargs)["ok"])


class ReferenceQueryTests(unittest.TestCase):
    def test_no_arguments_preserve_full_reference(self):
        r = impl.get_ref()
        self.assertEqual(r["counts"]["events"], 18)
        self.assertEqual(r["counts"]["functions"], 27)
        self.assertEqual(len(r["rules"]["must_pair"]), 4)

    def test_topic_and_case_insensitive_name(self):
        r = impl.get_ref(topic="event", name="KILLEDANYUNIT")
        self.assertTrue(r["found"])
        self.assertEqual(r["items"], ["killedAnyUnit"])
        self.assertNotIn("functions", r)
        self.assertLess(chars(r), chars(impl.get_ref()) / 3)

    def test_enum_key_and_value_queries(self):
        by_key = impl.get_ref(topic="enums", name="movementType")
        self.assertIn("LAND", by_key["items"]["movementtype"])
        by_value = impl.get_ref(topic="enums", name="infoOnly")
        self.assertEqual(by_value["items"], {"displaytype": ["infoOnly"]})

    def test_memory_arrays_and_sections(self):
        r = impl.get_ref(topic="memory", name="number[]")
        self.assertEqual(r["items"], ["number"])
        self.assertTrue(r["array"])
        self.assertEqual(list(impl.get_ref(topic="sections", name="[turret_main]")["items"]), ["E"])

    def test_rules_can_be_queried_by_key(self):
        r = impl.get_ref(topic="rules", name="alwaysSinglePress")
        self.assertTrue(r["found"])
        self.assertIn("canPlayerCancel", r["items"]["must_pair"][0]["keys"])
        r = impl.get_ref(topic="must_pair", name="alwaysSinglePress")
        self.assertEqual(len(r["items"]), 1)

    def test_unknown_names_do_not_claim_engine_does_not_support_them(self):
        r = impl.get_ref(topic="events", name="tookDamge")
        self.assertFalse(r["found"])
        self.assertIn("tookDamage", r["suggestions"])
        self.assertFalse(impl.get_ref(topic="ui")["ok"])
        self.assertFalse(impl.get_ref(name="tookDamage")["ok"])
        self.assertTrue(impl.get_ref(topic="functions", name="abs")["known_unavailable"])

    def test_math_extra_keeps_context_note(self):
        r = impl.get_ref(topic="math_extra", name="sqrt")
        self.assertTrue(r["found"])
        self.assertEqual(r["items"]["names"], ["sqrt"])
        self.assertTrue(r["items"]["note"])
        self.assertFalse(impl.get_ref(topic="math_extra", name="unknown")["found"])


def run_suite():
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    failed = len(result.failures) + len(result.errors)
    return result.testsRun - failed - len(result.skipped), failed


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _, failed = run_suite()
    sys.exit(bool(failed))

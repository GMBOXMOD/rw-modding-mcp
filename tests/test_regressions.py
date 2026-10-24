#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析、继承作用域和动作图回归；只依赖标准库，可独立执行。"""

import os
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rw_lint
import rw_explain
from rw_mcp import impl
from rw_test_support import find_test_mod


class FileCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rw-regression-")
        base = Path(self.temp.name).resolve()
        # 清理仅限本次生成的临时目录。
        assert base.parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {
            "RW_LINT_CACHE": "1", "RW_LINT_CACHE_DIR": str(base / "cache"),
        })
        env.start()
        self.addCleanup(env.stop)
        self.mod = base / "mod"
        self.write("mod-info.txt", "[mod]\ntitle: regression\nminVersion: 1.15\n")

    def write(self, name, text):
        path = self.mod / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def lint(self, target=None, incremental=True):
        result = rw_lint.run_lint(str(target or self.mod), incremental=incremental)
        self.assertTrue(result["ok"], result.get("error"))
        return result

    def issues(self, result, path=None):
        return [(i.level, i.code, i.line) for i in result["issues"]
                if path is None or os.path.abspath(i.path) == str(path.resolve())]

    def has(self, result, level, code, path=None):
        return any(lv == level and cd == code for lv, cd, _ in self.issues(result, path))


class ReferenceScopeTests(FileCase):
    def test_unrelated_projectile_cannot_satisfy_reference(self):
        a = self.write("a.ini", "[core]\nname: a\n[turret_main]\nprojectile: missing\n")
        self.write("b.ini", "[core]\nname: b\n[projectile_missing]\ndirectDamage: 1\n")
        for result in (self.lint(a), self.lint(), self.lint(incremental=False)):
            self.assertTrue(self.has(result, "error", "06", a))

    def test_unrelated_action_cannot_satisfy_reference(self):
        a = self.write("a.ini", "[core]\nname: a\n[action_start]\nalsoTriggerAction: work\n")
        self.write("b.ini", "[core]\nname: b\n[hiddenAction_work]\nautoTrigger: true\n")
        self.assertTrue(self.has(self.lint(), "warning", "05", a))

    def test_unrelated_defines_and_reads_do_not_hide_errors(self):
        a = self.write("a.ini", "[core]\nname: ${OTHER}\nprivateValue: 1\n")
        self.write("b.ini", "[core]\n@global OTHER: b\nname: ${core.privateValue}\n")
        result = self.lint()
        self.assertTrue(self.has(result, "warning", "09", a))
        self.assertTrue(self.has(result, "warning", "01", a))

    def test_relative_inheritance_with_space_in_filename(self):
        self.write("common unit.template", "[core]\n@global ID: a\n"
                   "[projectile_p]\ndirectDamage: 1\n[hiddenAction_work]\nautoTrigger: true\n")
        a = self.write("a.ini", '[core]\ncopyFrom: """common unit.template"""\nname: ${ID}\n'
                       "[turret_main]\nprojectile: p\n[action_start]\nalsoTriggerAction: work\n")
        result = self.lint(a)
        self.assertEqual(result["skipped"], [])
        self.assertEqual(result["files"], 1)
        self.assertFalse(self.has(result, "error", "06"))
        self.assertFalse(self.has(result, "warning", "05"))
        self.assertFalse(self.has(result, "warning", "09"))

    def test_multiline_copyfrom_loads_all_dependencies(self):
        self.write("one.template", "[projectile_p]\ndirectDamage: 1\n")
        self.write("two.template", "[hiddenAction_work]\nautoTrigger: true\n")
        a = self.write("a.ini", '[core]\ncopyFrom: """\none.template,\n two.template\n"""\n'
                       'name: a\n[turret_main]\nprojectile: p\n[action_start]\nalsoTriggerAction: work\n')
        result = self.lint(a)
        self.assertFalse(self.has(result, "error", "06"))
        self.assertFalse(self.has(result, "warning", "05"))
        self.assertEqual(result["skipped"], [])

    def test_root_and_transitive_inheritance_outside_scan(self):
        self.write("shared/leaf.template", "[projectile_p]\ndirectDamage: 1\n")
        self.write("shared/base.template", "[core]\ncopyFrom: leaf.template\n")
        a = self.write("units/a.ini", "[core]\ncopyFrom: ROOT:shared/base.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        result = self.lint(a)
        self.assertFalse(self.has(result, "error", "06"))
        self.assertEqual(result["skipped"], [])

    def test_nearest_units_template_shadows_parent(self):
        self.write("all-units.template", "[projectile_parent]\ndirectDamage: 1\n")
        self.write("units/all-units.template", "[projectile_local]\ndirectDamage: 1\n")
        a = self.write("units/sub/a.ini", "[core]\nname: a\n"
                       "[turret_one]\nprojectile: local\n"
                       "[turret_two]\nprojectile: parent\n")
        errors = [i.msg for i in self.lint(a)["issues"] if i.code == "06"]
        self.assertEqual(len(errors), 1)
        self.assertIn("parent", errors[0])

    def test_skipped_inherited_section_cannot_satisfy_reference(self):
        self.write("base.template", "[projectile_p]\n@copyFrom_skipThisSection: true\ndirectDamage: 1\n")
        a = self.write("a.ini", "[core]\ncopyFrom: base.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        self.assertTrue(self.has(self.lint(a), "error", "06"))

    def test_copyfrom_cycle_terminates(self):
        self.write("one.template", "[core]\ncopyFrom: two.template\n")
        self.write("two.template", "[core]\ncopyFrom: one.template\n[projectile_p]\ndirectDamage: 1\n")
        a = self.write("a.ini", "[core]\ncopyFrom: one.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        self.assertFalse(self.has(self.lint(a), "error", "06"))

    def test_external_template_edit_invalidates_cache(self):
        base = self.write("shared/base.template", "[projectile_p]\ndirectDamage: 1\n")
        a = self.write("units/a.ini", "[core]\ncopyFrom: ROOT:shared/base.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        self.assertFalse(self.has(self.lint(a), "error", "06"))
        self.assertEqual(self.lint(a)["cache"]["hits"], 1)
        base.write_text("[projectile_renamed]\ndirectDamage: 1\n", encoding="utf-8")
        changed = self.lint(a)
        self.assertEqual(changed["cache"]["misses"], 1)
        self.assertTrue(self.has(changed, "error", "06"))
        self.assertEqual(self.issues(changed), self.issues(self.lint(a, incremental=False)))

    def test_template_change_only_invalidates_dependent_unit(self):
        base = self.write("shared/base.template", "[projectile_p]\ndirectDamage: 1\n")
        a = self.write("units/a.ini", "[core]\ncopyFrom: ROOT:shared/base.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        self.write("units/b.ini", "[core]\nname: b\n")
        units = self.mod / "units"
        self.lint(units)
        self.assertEqual(self.lint(units)["cache"]["hits"], 2)
        base.write_text("[projectile_renamed]\ndirectDamage: 1\n", encoding="utf-8")
        result = self.lint(units)
        self.assertEqual(result["cache"]["hits"], 1)
        self.assertEqual(result["cache"]["misses"], 1)
        self.assertTrue(self.has(result, "error", "06", a))
        self.assertEqual(self.issues(result), self.issues(self.lint(units, incremental=False)))

    def test_missing_dependency_is_visible_and_new_file_invalidates_cache(self):
        a = self.write("a.ini", "[core]\ncopyFrom: absent.template\nname: a\n"
                       "[turret_main]\nprojectile: p\n")
        before = self.lint(a)
        self.assertTrue(before["skipped"])
        self.assertTrue(self.has(before, "error", "06"))
        self.write("absent.template", "[projectile_p]\ndirectDamage: 1\n")
        after = self.lint(a)
        self.assertFalse(after["skipped"])
        self.assertFalse(self.has(after, "error", "06"))


class CoreReferenceTests(FileCase):
    def setUp(self):
        super().setUp()
        self.core = Path(self.temp.name) / "original-units"
        self.core.mkdir()
        env = patch.dict(os.environ, {"RW_CORE_UNITS": str(self.core), "RW_GAME_JAR": ""})
        env.start()
        self.addCleanup(env.stop)

    def original(self, name, text):
        path = self.core / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def unit(self, name="a.ini", target="tanks/base.ini"):
        return self.write(name, "[core]\nname: a\ncopyFrom: CORE:" + target + "\n"
                          "[turret_main]\nprojectile: p\n")

    def test_loads_original_definitions_without_counting_original_as_unit(self):
        self.original("tanks/base.ini", "[core]\n@global ID: a\n[projectile_p]\ndirectDamage: 1\n"
                      "[hiddenAction_work]\nautoTrigger: true\n")
        a = self.write("a.ini", "[core]\nname: ${ID}\ncopyFrom: CORE:tanks/base.ini\n"
                       "[turret_main]\nprojectile: p\n[action_start]\nalsoTriggerAction: work\n")
        r = self.lint(a)
        self.assertEqual(r["files"], 1)
        self.assertEqual(r["errors"], 0)
        self.assertFalse(self.has(r, "warning", "05"))
        self.assertFalse(self.has(r, "warning", "09"))
        self.assertEqual(r["skipped"], [])
        self.assertEqual((r["core"]["references"], r["core"]["resolved"], r["core"]["unresolved"]), (1, 1, 0))
        self.assertEqual(r["core"]["mode"], "symbols_only")
        self.assertTrue(r["core"]["not_checked"])

    def test_nested_relative_inheritance_is_read(self):
        self.original("tanks/base.ini", "[core]\ncopyFrom: leaf.template\n")
        leaf = self.original("tanks/leaf.template", "[projectile_p]\ndirectDamage: 1\n")
        a = self.unit()
        r = self.lint(a)
        self.assertEqual(r["errors"], 0)
        self.assertEqual(r["skipped"], [])
        self.assertEqual(self.lint(a)["cache"]["hits"], 1)
        leaf.write_text("[projectile_p]\ndirectDamage: 20\n", encoding="utf-8")
        self.assertEqual(self.lint(a)["cache"]["misses"], 1)

    def test_missing_game_directory_is_incomplete_not_a_mod_error(self):
        a = self.write("a.ini", "[core]\nname: a\ncopyFrom: CORE:tanks/base.ini\n")
        with patch.dict(os.environ, {"RW_CORE_UNITS": str(self.core / "missing")}):
            r = self.lint(a)
        self.assertEqual(r["errors"], 0)
        self.assertIsNone(r["core"]["root"])
        self.assertEqual(r["core"]["unresolved"], 1)
        self.assertTrue(r["skipped"])

    def test_missing_original_is_reported_and_rechecked_after_creation(self):
        a = self.unit()
        r = self.lint(a)
        self.assertTrue(self.has(r, "error", "17"))
        self.assertEqual(r["core"]["unresolved"], 1)
        self.assertTrue(self.has(self.lint(a), "error", "17"))
        self.original("tanks/base.ini", "[projectile_p]\ndirectDamage: 1\n")
        after = self.lint(a)
        self.assertEqual(after["errors"], 0)
        self.assertEqual(after["skipped"], [])
        self.assertEqual(after["core"]["unresolved"], 0)

    def test_illegal_core_paths_are_rejected(self):
        for target in ("../outside.ini", "/outside.ini", "D:/outside.ini", r"\\server\outside.ini", ""):
            with self.subTest(target=target):
                r = self.lint(self.unit(target=target), incremental=False)
                self.assertTrue(self.has(r, "error", "17"))
                self.assertEqual(r["core"]["resolved"], 0)

    def test_resolved_link_must_stay_inside_original_directory(self):
        candidate = str(self.core.resolve() / "link.ini")
        outside = str(self.mod / "outside.ini")
        original = os.path.realpath
        with patch.object(rw_lint.os.path, "realpath", side_effect=lambda p: outside if str(p) == candidate else original(p)):
            with self.assertRaises(ValueError):
                rw_lint._core_target(str(self.core), "link.ini")

    def test_nested_core_copyfrom_cannot_escape(self):
        self.original("tanks/base.ini", "[core]\ncopyFrom: ../../outside.ini\n")
        self.write("outside.ini", "[projectile_p]\ndirectDamage: 1\n")
        r = self.lint(self.unit())
        self.assertTrue(self.has(r, "error", "17"))
        self.assertTrue(self.has(r, "error", "06"))

    def test_core_value_edit_only_invalidates_dependent_unit(self):
        original = self.original("tanks/base.ini", "[projectile_p]\ndirectDamage: 1\n")
        a = self.unit("units/a.ini")
        self.write("units/b.ini", "[core]\nname: b\n")
        units = self.mod / "units"
        self.lint(units)
        self.assertEqual(self.lint(units)["cache"]["hits"], 2)
        original.write_text("[projectile_p]\ndirectDamage: 200\n", encoding="utf-8")
        changed = self.lint(units)
        self.assertEqual((changed["cache"]["hits"], changed["cache"]["misses"]), (1, 1))
        self.assertEqual(self.issues(changed), self.issues(self.lint(units, incremental=False)))
        self.assertFalse(self.has(changed, "error", "06", a))

    def test_switching_original_directory_invalidates_cache(self):
        self.original("tanks/base.ini", "[projectile_p]\ndirectDamage: 1\n")
        a = self.unit()
        self.lint(a)
        self.assertEqual(self.lint(a)["cache"]["hits"], 1)
        other = Path(self.temp.name) / "other-units"
        (other / "tanks").mkdir(parents=True)
        (other / "tanks/base.ini").write_text("[projectile_p]\ndirectDamage: 2\n", encoding="utf-8")
        with patch.dict(os.environ, {"RW_CORE_UNITS": str(other)}):
            changed = self.lint(a)
        self.assertEqual(changed["cache"]["misses"], 1)
        self.assertEqual(changed["core"]["root"], str(other.resolve()))

    def test_explicit_directory_overrides_env_and_no_silent_fallback(self):
        missing = str(self.core / "missing")
        found = rw_lint.find_core_units(core_units=missing)
        self.assertIsNone(found["path"])
        self.assertEqual(found["source"], "argument")
        found = rw_lint.find_core_units()
        self.assertEqual(found["path"], str(self.core.resolve()))
        self.assertEqual(found["source"], "RW_CORE_UNITS")

    def test_detects_originals_from_game_jar_and_target(self):
        game = Path(self.temp.name) / "game"
        core = game / "assets/units"
        core.mkdir(parents=True)
        jar = game / "game-lib.jar"
        jar.write_bytes(b"")
        unit = game / "mods/units/mod/a.ini"
        unit.parent.mkdir(parents=True)
        unit.write_text("[core]\nname: a\n", encoding="utf-8")
        with patch.dict(os.environ, {"RW_CORE_UNITS": "", "RW_GAME_JAR": str(jar)}):
            self.assertEqual(rw_lint.find_core_units()["path"], str(core.resolve()))
        with patch.dict(os.environ, {"RW_CORE_UNITS": "", "RW_GAME_JAR": ""}), patch.object(rw_lint, "GAME_CANDIDATES", []):
            found = rw_lint.find_core_units(target=str(unit))
            self.assertEqual(found["path"], str(core.resolve()))
            self.assertEqual(found["source"], "target_ancestor")
        with patch.dict(os.environ, {"RW_CORE_UNITS": "", "RW_GAME_JAR": ""}), patch.object(rw_lint, "GAME_CANDIDATES", [str(game)]):
            self.assertEqual(rw_lint.find_core_units()["source"], "auto")

    def test_cli_and_mcp_expose_basic_mode_and_missing_targets(self):
        self.original("tanks/base.ini", "[projectile_p]\ndirectDamage: 1\n")
        a = self.unit()
        r = impl.lint(str(a))
        self.assertEqual(r["core"], self.lint(a)["core"])
        b = self.write("b.ini", "[core]\nname: b\n")
        batch = impl.lint(paths=[str(a), str(b)])
        self.assertNotIn("core", batch)
        self.assertEqual(batch["targets"][0]["core"]["resolved"], 1)
        self.assertNotIn("core", batch["targets"][1])
        cmd = [sys.executable, str(ROOT / "tools/rw_lint.py"), str(a), "--core-units", str(self.core), "--json", "--no-cache"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["core"], {**r["core"], "source": "argument"})
        self.unit(target="missing.ini")
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["core"]["unresolved"], 1)


class ParserTests(FileCase):
    def test_memory_expression_checked_in_all_block_forms(self):
        for key in ("setUnitMemory", "updateUnitMemory"):
            for value in ('x=abs(-1)', '"""x=abs(-1)"""', '"""\nx=abs(-1)\n"""'):
                with self.subTest(key=key, value=value):
                    a = self.write("a.ini", "[core]\nname: a\n[hiddenAction_tick]\n"
                                   + key + ": " + value + "\n")
                    self.assertIn(("warning", "16", 4), self.issues(self.lint(a)))

    def test_crlf_block_joins_like_engine(self):
        a = self.mod / "a.ini"
        a.write_bytes(b'[core]\r\nname: a\r\n[hiddenAction_tick]\r\n'
                      b'setUnitMemory: """x=ab\r\ns(-1)"""\r\n')
        self.assertIn(("warning", "16", 4), self.issues(self.lint(a)))
        self.assertEqual(rw_lint.parse_file(str(a))[1][-1][2], "x=abs(-1)")

    def test_single_line_block_still_checks_key_and_value(self):
        a = self.write("a.ini", '[core]\nname: a\nmaxHp: """wrong"""\n')
        self.assertIn(("error", "09", 3), self.issues(self.lint(a)))

    def test_comments_with_quotes_do_not_hide_following_checks(self):
        a = self.write("a.ini", '[core]\nname: a\n# """ comment\nmaxHp： 1\nname: ${bad\n')
        result = self.lint(a)
        self.assertTrue(self.has(result, "error", "02"))
        self.assertTrue(self.has(result, "error", "04"))
        self.assertFalse(self.has(result, "error", "03"))

    def test_standalone_block_comment_is_not_code(self):
        a = self.write("a.ini", '[core]\nname: a\n"""\n[hiddenAction_fake]\n'
                       'setUnitMemory: x=abs(-1)\n@memory bad: invalid\nname: ${unclosed\n"""\n')
        self.assertEqual(self.issues(self.lint(a)), [])
        result = rw_explain.explain(str(a), as_json=True)
        self.assertEqual(result["memory_declared"], {})
        self.assertNotIn("hiddenAction_fake", result["nodes"])

    def test_block_directive_and_following_section_survive(self):
        a = self.write("a.ini", '[core]\n@global ID: """a"""\nname: ${ID}\n'
                       '[hiddenAction_tick]\nsetUnitMemory: """x=1"""\n')
        full = rw_lint.parse_file(str(a), use_cache=False)
        self.assertIn("id", full[5])
        self.assertEqual(full[1][-1], (5, "setUnitMemory", "x=1", "hiddenAction_tick"))
        self.assertFalse(self.has(self.lint(a), "warning", "09"))

    def test_balanced_placeholder_cannot_cancel_unclosed_one(self):
        for value in ("${x} ${y", "${x} ${y} ${z", "%{${x}", "${x} %{y"):
            with self.subTest(value=value):
                a = self.write("a.ini", "[core]\nname: " + value + "\n")
                self.assertIn(("error", "04", 2), self.issues(self.lint(a)))

    def test_balanced_nested_placeholders_are_accepted(self):
        a = self.write("a.ini", "[core]\n@global x: 1\nname: %{select(${x}, 1, 2)} ${x}\n")
        self.assertFalse(self.has(self.lint(a), "error", "04"))

    def test_separate_values_cannot_balance_each_other(self):
        a = self.write("a.ini", "[core]\nname: ${x\nprice: }\n")
        errors = [(cd, ln) for lv, cd, ln in self.issues(self.lint(a)) if cd == "04"]
        self.assertEqual(errors, [("04", 2), ("04", 3)])

    def test_multiline_placeholder_is_checked_as_one_value(self):
        for value, want_error in (('"""\n${x\n}\n"""', False), ('"""\n${x} ${y\n"""', True)):
            with self.subTest(value=value):
                a = self.write("a.ini", "[core]\n@global x: 1\nname: " + value + "\n")
                self.assertEqual(self.has(self.lint(a), "error", "04"), want_error)

    def test_unclosed_triple_quote_is_reported(self):
        a = self.write("a.ini", '[core]\nname: a\nmaxHp: """\n10\n')
        self.assertTrue(self.has(self.lint(a), "error", "03"))


class ActionGraphTests(FileCase):
    def explain(self, text):
        a = self.write("a.ini", text)
        result = rw_explain.explain(str(a), as_json=True)
        self.assertTrue(result["ok"], result.get("error"))
        return a, result

    def test_conditions_and_repeat_record_memory_reads(self):
        keys = ("autoTrigger", "autoTriggerOnEvent", "requireConditional",
                "alsoTriggerActionRepeat", "alsoTriggerActionConditional",
                "alsoTriggerOrQueueActionConditional")
        for key in keys:
            with self.subTest(key=key):
                _, result = self.explain("[core]\nname: a\n@memory x: number\n"
                                         "[action_start]\n" + key + ": if memory.x>0\n")
                self.assertIn("x", result["nodes"]["action_start"]["memory_reads"])
                self.assertIn("uninit-memory", [f["rule"] for f in result["findings"]])

    def test_function_memory_read_in_condition(self):
        for expr in ('readUnitMemory(name="x", type="number")',
                     'readUnitMemory(type="number", name="x")', 'readUnitMemory("x")'):
            with self.subTest(expr=expr):
                _, result = self.explain("[core]\nname: a\n@memory x: number\n"
                                         "[action_start]\nrequireConditional: if " + expr + ">0\n")
                self.assertEqual(result["nodes"]["action_start"]["memory_reads"], ["x"])

    def test_assignment_index_is_a_memory_read(self):
        _, result = self.explain("[core]\nname: a\n@memory i: number\n@memory arr: number[]\n"
                                 "[action_start]\nsetUnitMemory: arr[memory.i]=1\n")
        self.assertEqual(result["nodes"]["action_start"]["memory_reads"], ["i"])
        self.assertEqual([f["rule"] for f in result["findings"]], ["uninit-memory"])

    def test_written_memory_does_not_report_uninitialized(self):
        _, result = self.explain("[core]\nname: a\n@memory x: number\n[action_start]\n"
                                 "autoTrigger: if memory.x>0\nsetUnitMemory: x=1\n")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["entries"], ["action_start"])

    def test_button_chain_is_rendered_by_default(self):
        a, result = self.explain("[core]\nname: a\n@memory x: number\n[action_start]\n"
                                 "alsoTriggerAction: work\n[hiddenAction_work]\nsetUnitMemory: x=1\n")
        self.assertEqual(result["entries"], ["action_start"])
        self.assertEqual(result["findings"], [])
        text = rw_explain.render_text(result)
        self.assertIn("player button", text)
        self.assertIn("alsoTriggerAction", text)
        self.assertIn("write  : x", text)
        self.assertNotIn("未被任何触发链引用", text)
        for fmt in ("text", "json", "both"):
            response = impl.explain_actions(str(a), fmt=fmt)
            self.assertTrue(response["ok"])
            self.assertEqual(response["summary"]["entries"], 1)
            if fmt != "json":
                self.assertIn("alsoTriggerAction", response["text"])

    def test_explicit_action_filter_still_works(self):
        _, result = self.explain("[core]\nname: a\n[action_start]\nalsoTriggerAction: work\n"
                                 "[hiddenAction_work]\nsetUnitMemory: x=1\n")
        text = rw_explain.render_text(result, "work")
        self.assertIn("hiddenAction_work", text)
        self.assertNotIn("player button", text)


class ExternalModDiscoveryTests(FileCase):
    def test_finds_sibling_sample(self):
        project = self.mod / "repository"
        project.mkdir()
        sample = self.mod / "sample"
        sample.mkdir()
        with patch.dict(os.environ, {"RW_TEST_MOD_ROOTS": ""}):
            self.assertEqual(find_test_mod("sample", str(project)), str(sample))

    def test_explicit_roots_take_precedence(self):
        project = self.mod / "repository"
        local = project / "sample"
        local.mkdir(parents=True)
        external = self.mod / "external"
        sample = external / "sample"
        sample.mkdir(parents=True)
        roots = str(self.mod / "missing") + os.pathsep + str(external)
        with patch.dict(os.environ, {"RW_TEST_MOD_ROOTS": roots}):
            self.assertEqual(find_test_mod("sample", str(project)), str(sample))

    def test_missing_sample_returns_none(self):
        with patch.dict(os.environ, {"RW_TEST_MOD_ROOTS": ""}):
            self.assertIsNone(find_test_mod("missing-sample", str(self.mod)))


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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""challenge_audit.py 的单元测试（仅用标准库 unittest）。

运行：
    python -m unittest discover -s tests -v
或：
    python -m unittest tests.test_challenge_audit -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# 保证从仓库根目录或任意目录运行都能导入主模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import challenge_audit as ca  # noqa: E402


class TestParseItems(unittest.TestCase):
    def test_comma_string(self):
        self.assertEqual(ca.parse_items("README.md,*repo链接*, *AI日志* "),
                         ["README.md", "*repo链接*", "*AI日志*"])

    def test_list(self):
        self.assertEqual(ca.parse_items(["a.md", " b.md ", ""]), ["a.md", "b.md"])

    def test_none_and_empty(self):
        self.assertEqual(ca.parse_items(None), [])
        self.assertEqual(ca.parse_items("  , , "), [])


class TestGlob(unittest.TestCase):
    def test_basename_star(self):
        rx = ca.glob_to_regex("*repo链接*")
        self.assertTrue(rx.match("lsa_C5_repo链接.md"))
        self.assertFalse(rx.match("readme.md"))

    def test_exact_name(self):
        rx = ca.glob_to_regex("README.md")
        self.assertTrue(rx.match("README.md"))
        self.assertFalse(rx.match("docs/README.md"))

    def test_path_star_does_not_cross_slash(self):
        # 含 '/' 时，* 只匹配一层，不跨目录分隔符
        hits = ca.match("docs/*.md", ["docs/guide.md", "docs/sub/deep.md"], [])
        self.assertEqual(hits, ["docs/guide.md"])

    def test_double_star_crosses_slash(self):
        # **/ 表示「零或多层目录」，既匹配根也匹配深层
        hits = ca.match("**/*.md", ["README.md", "docs/guide.md", "docs/sub/deep.md"], [])
        self.assertEqual(hits, ["README.md", "docs/guide.md", "docs/sub/deep.md"])

    def test_directory_pattern(self):
        hits = ca.match(".github/ISSUE_TEMPLATE/", [], [".github/ISSUE_TEMPLATE"])
        self.assertEqual(hits, [".github/ISSUE_TEMPLATE"])

    def test_question_mark(self):
        self.assertTrue(ca.glob_to_regex("test_?.py").match("test_1.py"))


class TestScan(unittest.TestCase):
    def test_skips_noise_dirs_and_excludes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ["README.md", "src/main.py", ".git/config",
                        "__pycache__/x.pyc", "notes.log", "src/skip.tmp"]:
                p = Path(tmp) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")
            files, dirs = ca.scan(tmp, ["*.log", "*.tmp"])
            self.assertIn("README.md", files)
            self.assertIn("src/main.py", files)
            self.assertNotIn(".git/config", files)
            self.assertNotIn("__pycache__/x.pyc", files)
            self.assertNotIn("notes.log", files)
            self.assertNotIn("src/skip.tmp", files)
            self.assertNotIn(".git", dirs)


class TestLoadJson(unittest.TestCase):
    def test_bom_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bom.json"
            p.write_text('\ufeff{"title": "BOM测试"}', encoding="utf-8")
            data, err = ca.load_json(str(p))
            self.assertIsNone(err)
            self.assertEqual(data["title"], "BOM测试")

    def test_invalid_json_reports_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text('{"x": }', encoding="utf-8")
            data, err = ca.load_json(str(p))
            self.assertEqual(data, {})
            self.assertIn("JSON 解析失败", err)
            self.assertIn(":", err)


class TestEvaluate(unittest.TestCase):
    def test_required_pass_and_fail(self):
        req, _ = ca.evaluate(["README.md", "*AI日志*"],
                             ["README.md", "lsa_C5_AI日志.md"], [], missing_hints=True)
        self.assertEqual(req[0].status, ca.PASS)
        self.assertEqual(req[1].status, ca.PASS)
        self.assertEqual(req[1].matched, ["lsa_C5_AI日志.md"])

    def test_missing_gets_hint(self):
        req, _ = ca.evaluate(["*拿来说明*"], ["README.md"], [], missing_hints=True)
        self.assertEqual(req[0].status, ca.FAIL)
        self.assertIn("lsa_C5", req[0].hint)


class TestRedFlags(unittest.TestCase):
    def test_missing_artifacts(self):
        req, _ = ca.evaluate(["README.md"], [], [], missing_hints=True)
        flags = ca.detect_red_flags([], [], ".", req)
        self.assertTrue(any("missing_artifacts" in f for f in flags))

    def test_no_ai_log(self):
        req, _ = ca.evaluate(["README.md"], ["README.md"], [], missing_hints=True)
        flags = ca.detect_red_flags(["README.md"], [], ".", req)
        self.assertTrue(any("no_ai_log" in f for f in flags))

    def test_one_shot_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "AI_LOG.md").write_text("- [2026-11-01] 一句话", encoding="utf-8")
            req, _ = ca.evaluate(["README.md"], ["README.md", "AI_LOG.md"], [], missing_hints=True)
            flags = ca.detect_red_flags(["README.md", "AI_LOG.md"], [], tmp, req)
            self.assertTrue(any("one_shot_ai" in f for f in flags))


class TestRender(unittest.TestCase):
    def test_markdown_has_all_sections(self):
        spec = {"title": "T", "challenge_id": "C5"}
        req = [ca.Check("README.md", "README.md", ca.PASS, ["README.md"])]
        opt = [ca.Check("LICENSE", "LICENSE", ca.FAIL)]
        md = ca.render_md(spec, req, opt, ["- hint"], [],
                          {"dir": ".", "spec_source": "s", "rubric_source": "r"}, "")
        for section in ["## 总览", "## 必交项勾选表", "## 缺失清单",
                        "## 可选项 / 加分项", "## Rubric 信号自评提示",
                        "## 红旗检查", "## 下一步"]:
            self.assertIn(section, md)

    def test_json_is_parseable(self):
        spec = {"title": "T", "challenge_id": "C5"}
        req = [ca.Check("README.md", "README.md", ca.PASS, ["README.md"])]
        out = ca.render_json(spec, req, [], [], [],
                             {"dir": ".", "spec_source": "s", "rubric_source": "r"})
        data = json.loads(out)
        self.assertEqual(data["summary"]["required_pct"], 100.0)
        self.assertEqual(len(data["checks"]), 1)


class TestMainExitCodes(unittest.TestCase):
    def test_missing_dir_returns_2(self):
        self.assertEqual(ca.main(["/definitely/not/a/dir"]), 2)

    def test_demo_bad_returns_1(self):
        demo = Path(__file__).resolve().parents[1] / "examples" / "demo-bad"
        self.assertEqual(ca.main([str(demo), "--no-timestamp"]), 1)

    def test_demo_good_returns_0(self):
        demo = Path(__file__).resolve().parents[1] / "examples" / "demo-good"
        self.assertEqual(ca.main([str(demo), "--no-timestamp"]), 0)

    def test_out_file_roundtrip(self):
        demo = Path(__file__).resolve().parents[1] / "examples" / "demo-good"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.md"
            code = ca.main([str(demo), "--no-timestamp", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertIn("提交前自查审计报告", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

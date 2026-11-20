#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""challenge_audit.py — 挑战交付物「提交前自查」工具（零第三方依赖）。

一句话：输入一个挑战资料包目录，输出一份 Markdown / JSON 自查审计报告。

它解决一个真实的小痛点：挑战说明里列了一堆「必交文件」和 rubric 评分维度，
提交前靠人眼逐条核对既慢又容易漏。本工具把规则写成 challenge.json / rubric.json，
扫描目录做 glob 匹配，秒级给出勾选表、缺失清单、完成度与 rubric 信号自评。

特点
----
* 仅用 Python 标准库（argparse / json / os / re / sys / fnmatch / dataclasses /
  pathlib / typing / datetime），无需 pip install，Python 3.8+ 即可运行。
* 跨平台：路径统一用 POSIX 相对路径表示，读写文件一律显式 encoding。
* 可当 CI 门：--format json --strict，存在 FAIL（或 WARN 且 --strict）时退出码 1。
* 可复现：--no-timestamp 让同一输入产生逐字节一致的输出。

用法
----
    python challenge_audit.py <目录> [--config PATH] [--rubric PATH]
                              [--out PATH] [--format {md,json}]
                              [--strict] [--exclude GLOB] [--no-timestamp]

退出码：0 = 必交项全 PASS；1 = 存在 FAIL（或 --strict 下有 WARN）；2 = 配置 / IO 错误。
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # Windows 控制台默认编码可能不是 UTF-8，尽量纠正；失败则静默降级
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - 只在极老版本触发
    pass

VERSION = "1.0.0"
PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
             ".idea", ".vscode", ".pytest_cache", ".mypy_cache", ".tox"}

# 内置默认清单：目标目录没有 challenge.json 时仍能运行（报告里会给出 WARN）。
BUILTIN_REQUIRED = ["README.md", "*repo链接*", "*AI日志*", "*拿来说明*"]
BUILTIN_OPTIONAL = ["LICENSE", ".gitignore", "AI_LOG.md", "ATTRIBUTION.md",
                    "AAR.md", "CHANGELOG.md", "CONTRIBUTING.md",
                    ".github/ISSUE_TEMPLATE/*"]

# 字符串型 rubric 信号的兜底识别：从中文/英文信号描述里猜出要找的文件。
_SIGNAL_HINTS: Sequence[Tuple[str, str]] = (
    ("README", "README.md"), ("readme", "README.md"),
    ("License", "LICENSE"), ("LICENSE", "LICENSE"), ("协议", "LICENSE"),
    ("贡献指南", "CONTRIBUTING.md"), ("CONTRIBUTING", "CONTRIBUTING.md"),
    ("issue", ".github/ISSUE_TEMPLATE/"), ("Issue", ".github/ISSUE_TEMPLATE/"),
    ("版本管理", "CHANGELOG.md"), ("CHANGELOG", "CHANGELOG.md"), ("tag", "CHANGELOG.md"),
    ("AI", "AI_LOG.md"), ("拿来", "ATTRIBUTION.md"), ("ATTRIBUTION", "ATTRIBUTION.md"),
    ("结构清晰", "README.md"), ("可运行", "*.py"),
)


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    """一个清单项的检查结果。"""

    item: str                              # 原始清单项文本
    pattern: str                           # 归一化后的匹配模式
    status: str                            # PASS / FAIL / WARN
    matched: List[str] = field(default_factory=list)   # 命中的相对路径
    hint: str = ""                         # 给人的下一步建议


class ConfigError(Exception):
    """配置或 IO 错误（对应退出码 2）。"""


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def parse_items(value: Any) -> List[str]:
    """清单项既可能是数组，也可能是逗号分隔字符串（EduSeed 导出的是后者）。

    >>> parse_items("README.md,*repo链接*, *AI日志* ")
    ['README.md', '*repo链接*', '*AI日志*']
    >>> parse_items(["a.md", "b.md"])
    ['a.md', 'b.md']
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [p.strip() for p in value.split(",") if p.strip()]
    return [str(value).strip()]


def load_json(path: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """读取 JSON；兼容 UTF-8 BOM。返回 (数据, 错误信息或 None)。"""
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return {}, f"{path}: 顶层必须是 JSON 对象，实际为 {type(data).__name__}"
        return data, None
    except FileNotFoundError:
        return {}, f"文件不存在: {path}"
    except json.JSONDecodeError as exc:
        return {}, f"{path}:{exc.lineno}:{exc.colno}: JSON 解析失败: {exc.msg}"
    except (OSError, UnicodeError) as exc:
        return {}, f"{path}: 读取失败: {exc}"


def scan(root: str, excludes: Sequence[str]) -> Tuple[List[str], List[str]]:
    """遍历目录，返回 (文件相对路径列表, 目录相对路径列表)。

    路径一律用 '/' 分隔（即使在 Windows 上），并跳过常见噪声目录。
    """
    files: List[str] = []
    dirs: List[str] = []
    for base, subdirs, names in os.walk(root, followlinks=False):
        subdirs[:] = sorted(
            d for d in subdirs
            if d not in SKIP_DIRS and not any(fnmatch.fnmatch(d, ex) for ex in excludes)
        )
        rel = os.path.relpath(base, root).replace(os.sep, "/")
        if rel != ".":
            dirs.append(rel)
        for name in sorted(names):
            if any(fnmatch.fnmatch(name, ex) for ex in excludes):
                continue
            path = f"{rel}/{name}" if rel != "." else name
            files.append(path)
    return files, dirs


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """把受限 glob 翻译成正则。

    * 模式含 '/'：按整条相对路径匹配，`*` 不跨 `/`，`**` 跨 `/`。
    * 模式不含 '/'：按文件名（basename）匹配，`*` 可匹配任意字符。
    * 以 '/' 结尾：匹配目录。
    """
    is_dir = pattern.endswith("/")
    pat = pattern.rstrip("/")
    has_slash = "/" in pat
    out: List[str] = []
    i = 0
    while i < len(pat):
        ch = pat[i]
        if ch == "*":
            if pat[i:i + 2] == "**":
                if i + 2 < len(pat) and pat[i + 2] == "/":
                    out.append("(?:.*/)?")   # **/ 表示「零或多层目录」
                    i += 3
                else:
                    out.append(".*")
                    i += 2
            else:
                out.append("[^/]*" if has_slash else ".*")
                i += 1
        elif ch == "?":
            out.append("[^/]" if has_slash else ".")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    tail = "/$" if is_dir else "$"
    return re.compile("^" + "".join(out) + tail)


def match(pattern: str, files: Sequence[str], dirs: Sequence[str]) -> List[str]:
    """返回匹配某个 glob 的所有相对路径（排序后）。"""
    pat = pattern.rstrip("/")
    is_dir = pattern.endswith("/")
    has_slash = "/" in pat
    rx = glob_to_regex(pattern)
    pool = dirs if is_dir else files
    hits: List[str] = []
    for path in pool:
        if is_dir:
            target = path + "/"
        elif has_slash:
            target = path
        else:
            target = PurePosixPath(path).name
        if rx.match(target):
            hits.append(path)
    return sorted(hits)


def read_text(root: str, rel: str) -> str:
    """尽力读取文本；任何失败都返回空串（不因权限问题中断整份报告）。"""
    try:
        with open(os.path.join(root, rel.replace("/", os.sep)),
                  "r", encoding="utf-8-sig") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return ""


# --------------------------------------------------------------------------- #
# 评估
# --------------------------------------------------------------------------- #
def evaluate(items: Sequence[str], files: Sequence[str], dirs: Sequence[str],
             missing_hints: bool) -> Tuple[List[Check], List[Check]]:
    """把清单项逐个匹配到实际文件。必交项 FAIL，可选项 WARN。"""
    required: List[Check] = []
    optional: List[Check] = []
    for raw in items:
        pattern = raw
        hits = match(pattern, files, dirs)
        check = Check(item=raw, pattern=pattern,
                      status=PASS if hits else FAIL, matched=hits)
        if not hits and missing_hints:
            check.hint = f"新建匹配 `{pattern}` 的文件（建议命名 lsa_C5_…）."
        required.append(check)
    return required, optional


def rubric_signals(rubric: Dict[str, Any], files: Sequence[str],
                   dirs: Sequence[str], root: str) -> List[str]:
    """对每个 rubric 维度统计信号命中情况，输出人类可读的自评提示。

    结构化信号（dict）：type ∈ {file, regex, count_min, prefix}。
    字符串信号（EduSeed 原始格式）：用 _SIGNAL_HINTS 兜底猜测，猜不到就诚实标注。
    """
    hints: List[str] = []
    for dim in rubric.get("dimensions", []):
        if not isinstance(dim, dict):
            continue
        name = str(dim.get("name") or dim.get("label") or dim.get("key") or "维度")
        key = str(dim.get("key") or dim.get("id") or "")
        maximum = dim.get("max", dim.get("maxPoints", ""))
        signals = dim.get("signals", [])
        hit = 0
        unknown = 0
        detail: List[str] = []
        for sig in signals:
            ok, label = _check_signal(sig, files, dirs, root)
            if ok is None:
                unknown += 1
                detail.append(f"?{label}")
            else:
                hit += int(ok)
                detail.append(("✓" if ok else "✗") + label)
        total = len(signals)
        known = total - unknown
        if key:
            head = f"- **{key}**（{name}）"
        else:
            head = f"- **{name}**"
        if maximum != "":
            head += f" 满分 {maximum}"
        head += f"：信号 {hit}/{known}" + (f"，另有 {unknown} 项需人工核对" if unknown else "")
        hints.append(head + "　`" + " ".join(detail) + "`")
    return hints


def _check_signal(sig: Any, files: Sequence[str], dirs: Sequence[str],
                  root: str) -> Tuple[Optional[bool], str]:
    """返回 (是否命中 或 None 表示无法判定, 简述)。"""
    if isinstance(sig, dict):
        stype = str(sig.get("type", "file"))
        target = str(sig.get("target", ""))
        if not target:
            return None, "空目标"
        hits = match(target, files, dirs)
        if stype == "file":
            return bool(hits), target
        if stype == "regex":
            pattern = str(sig.get("pattern", ""))
            ok = any(re.search(pattern, read_text(root, f)) for f in hits)
            return ok, f"{target}~/{pattern}/"
        if stype == "count_min":
            try:
                need = int(sig.get("min", 1))
            except (TypeError, ValueError):
                need = 1
            return len(hits) >= need, f"{target}≥{need}"
        if stype == "prefix":
            return bool(match(target if target.endswith("/") else target + "/", files, dirs)), target
        return None, f"未知type={stype}"
    # 字符串信号：尽力猜测文件名
    text = str(sig)
    for keyword, pattern in _SIGNAL_HINTS:
        if keyword in text:
            return bool(match(pattern, files, dirs)), pattern
    return None, text[:12]


def detect_red_flags(files: Sequence[str], dirs: Sequence[str],
                     root: str, required: Sequence[Check]) -> List[str]:
    """检测三类红旗：核心缺失 / 无 AI 日志 / 疑似 one-shot。"""
    flags: List[str] = []
    if any(c.status == FAIL for c in required):
        flags.append("missing_artifacts：存在未满足的必交项")
    ai_logs = match("*AI日志*", files, []) + match("AI_LOG.md", files, [])
    if not ai_logs:
        flags.append("no_ai_log：未发现 AI 使用记录")
    else:
        body = "\n".join(read_text(root, f) for f in sorted(set(ai_logs)))
        stamps = re.findall(r"\[\d{4}-\d{2}-\d{2}", body)
        if len(stamps) < 3:
            flags.append("one_shot_ai：AI 日志时间戳少于 3 条，疑似一次性提交")
    return flags


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #
def _summary(required: Sequence[Check], optional: Sequence[Check],
             flags: Sequence[str]) -> Dict[str, Any]:
    req_ok = sum(1 for c in required if c.status == PASS)
    opt_ok = sum(1 for c in optional if c.status == PASS)
    return {
        "required_pass": req_ok,
        "required_total": len(required),
        "required_pct": round(100.0 * req_ok / len(required), 1) if required else 0.0,
        "optional_present": opt_ok,
        "optional_total": len(optional),
        "red_flags": list(flags),
    }


def render_md(spec: Dict[str, Any], required: Sequence[Check],
              optional: Sequence[Check], hints: Sequence[str], flags: Sequence[str],
              meta: Dict[str, Any], stamp: str) -> str:
    """渲染 Markdown 报告（纯字符串拼接，换行固定为 \\n）。"""
    s = _summary(required, optional, flags)
    title = spec.get("title") or spec.get("challenge_id") or "挑战"
    lines: List[str] = []
    lines.append(f"# 提交前自查审计报告 — {title}")
    lines.append("")
    lines.append(f"- 目标目录：`{meta['dir']}`")
    lines.append(f"- 清单来源：{meta['spec_source']}")
    lines.append(f"- Rubric 来源：{meta['rubric_source']}")
    if stamp:
        lines.append(f"- 生成时间：{stamp}")
    lines.append("")
    lines.append("> 本报告只校验**文件是否存在、结构信号是否出现**，不判断内容的语义正确性。")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append("| 项 | 结果 |")
    lines.append("|---|---|")
    lines.append(f"| 必交项 | {s['required_pass']}/{s['required_total']} PASS（{s['required_pct']}%） |")
    lines.append(f"| 可选项 | {s['optional_present']}/{s['optional_total']} 已具备 |")
    lines.append(f"| 红旗 | {len(flags)} 触发 |".replace(" 触发", " 项触发"))
    lines.append("")

    lines.append("## 必交项勾选表")
    lines.append("")
    lines.append("| 状态 | 要求 | 匹配模式 | 命中文件 |")
    lines.append("|---|---|---|---|")
    for c in required:
        status = "✅ PASS" if c.status == PASS else "❌ FAIL"
        found = ", ".join(f"`{m}`" for m in c.matched[:5]) if c.matched else "—"
        if len(c.matched) > 5:
            found += f" 等 {len(c.matched)} 项"
        lines.append(f"| {status} | {c.item} | `{c.pattern}` | {found} |")
    lines.append("")

    missing = [c for c in required if c.status == FAIL]
    lines.append("## 缺失清单")
    lines.append("")
    if not missing:
        lines.append("_无缺失，全部必交项已满足。_")
    else:
        for idx, c in enumerate(missing, 1):
            lines.append(f"{idx}. `{c.pattern}` → {c.hint or '请补齐该交付物。'}")
    lines.append("")

    if optional:
        lines.append("## 可选项 / 加分项")
        lines.append("")
        lines.append("| 状态 | 加分项 | 命中文件 |")
        lines.append("|---|---|---|")
        for c in optional:
            status = "✅" if c.status == PASS else "⬜ 待补"
            found = ", ".join(f"`{m}`" for m in c.matched[:3]) if c.matched else "—"
            lines.append(f"| {status} | {c.item} | {found} |")
        lines.append("")

    if hints:
        lines.append("## Rubric 信号自评提示")
        lines.append("")
        lines.extend(hints)
        lines.append("")

    lines.append("## 红旗检查")
    lines.append("")
    if flags:
        for f in flags:
            lines.append(f"- 🚩 {f}")
    else:
        lines.append("- ✅ 未触发红旗。")
    lines.append("")

    lines.append("## 下一步（按优先级）")
    lines.append("")
    actions: List[str] = []
    for c in missing:
        actions.append(f"补齐必交项 `{c.pattern}`。")
    if len(flags) > len(missing):
        actions.append("处理上节列出的红旗（尤其是 AI 日志迭代记录）。")
    for c in optional:
        if c.status != PASS and "ISSUE_TEMPLATE" in c.pattern:
            actions.append("补 `.github/ISSUE_TEMPLATE/` 提升社区要素得分。")
            break
    if not actions:
        actions.append("提交前再跑一次 `python challenge_audit.py . --strict` 固化结果，并打版本 tag。")
    for idx, act in enumerate(actions, 1):
        lines.append(f"{idx}. {act}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_由 challenge_audit.py v{VERSION} 生成 · 仅校验存在性与结构信号 · 输出不含主观评分_")
    lines.append("")
    return "\n".join(lines)


def render_json(spec: Dict[str, Any], required: Sequence[Check],
                optional: Sequence[Check], hints: Sequence[str], flags: Sequence[str],
                meta: Dict[str, Any]) -> str:
    """渲染机器可读 JSON，供 CI 消费。"""
    payload = {
        "meta": {
            "challenge_id": spec.get("challenge_id", ""),
            "title": spec.get("title", ""),
            "dir": meta["dir"],
            "spec_source": meta["spec_source"],
            "rubric_source": meta["rubric_source"],
            "version": VERSION,
        },
        "checks": [
            {"item": c.item, "pattern": c.pattern, "status": c.status,
             "matched": c.matched, "hint": c.hint, "kind": "required"}
            for c in required
        ] + [
            {"item": c.item, "pattern": c.pattern, "status": c.status,
             "matched": c.matched, "kind": "optional"}
            for c in optional
        ],
        "rubric_hints": list(hints),
        "red_flags": list(flags),
        "summary": _summary(required, optional, flags),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="challenge_audit.py",
        description="挑战交付物提交前自查工具：输入目录，输出 Markdown / JSON 审计报告。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  python challenge_audit.py .\n"
               "  python challenge_audit.py examples/demo-bad --format json --strict\n"
               "  python challenge_audit.py . --no-timestamp --out report.md\n",
    )
    parser.add_argument("dir", nargs="?", default=".", help="待审计目录（默认当前目录）")
    parser.add_argument("--config", help="challenge.json 路径（默认 <dir>/challenge.json）")
    parser.add_argument("--rubric", help="rubric.json 路径（默认 <dir>/rubric.json）")
    parser.add_argument("--out", help="输出文件（默认打印到标准输出）")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="输出格式（默认 md）")
    parser.add_argument("--strict", action="store_true", help="可选项缺失（WARN）也视为失败")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="额外排除模式，可重复指定")
    parser.add_argument("--no-timestamp", action="store_true", help="去掉生成时间，输出可逐字节复现")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.dir

    if not os.path.isdir(root):
        print(f"ERROR: 目录不存在或不是目录: {root}", file=sys.stderr)
        return 2

    # ---- 读取 spec ----
    config_path = args.config or os.path.join(root, "challenge.json")
    spec, spec_err = load_json(config_path)
    if spec_err and args.config:
        print(f"ERROR: {spec_err}", file=sys.stderr)
        return 2
    warnings: List[str] = []
    if spec_err:
        spec = {"challenge_id": "C5", "title": "GitHub Repository（内置默认清单）"}
        spec_source = f"内置默认清单（{spec_err}）"
        warnings.append(spec_err)
    else:
        spec_source = config_path

    # ---- 读取 rubric ----
    rubric_path = args.rubric or os.path.join(root, "rubric.json")
    rubric, rubric_err = load_json(rubric_path)
    if rubric_err:
        rubric = {}
        rubric_source = f"无（{rubric_err}）"
        warnings.append(rubric_err)
    else:
        rubric_source = rubric_path

    # ---- 扫描 + 匹配 ----
    files, dirs = scan(root, args.exclude)
    req_items = parse_items(spec.get("required_deliverables"))
    if not req_items:
        req_items = list(BUILTIN_REQUIRED)
        warnings.append("challenge.json 未声明 required_deliverables，采用内置默认清单")
    opt_items = parse_items(spec.get("optional_deliverables"))
    if not opt_items and "required_deliverables" in spec:
        opt_items = list(BUILTIN_OPTIONAL)

    required, _ = evaluate(req_items, files, dirs, missing_hints=True)
    optional, _ = evaluate(opt_items, files, dirs, missing_hints=False)
    hints = rubric_signals(rubric, files, dirs, root)
    flags = detect_red_flags(files, dirs, root, required)
    flags.extend(f"config_warn：{w}" for w in warnings)

    stamp = "" if args.no_timestamp else datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = {"dir": root, "spec_source": spec_source, "rubric_source": rubric_source}

    if args.format == "json":
        output = render_json(spec, required, optional, hints, flags, meta)
    else:
        output = render_md(spec, required, optional, hints, flags, meta, stamp)

    # ---- 输出 ----
    if args.out:
        out_abs = os.path.abspath(args.out)
        for protected in (os.path.abspath(config_path), os.path.abspath(rubric_path)):
            if out_abs == protected:
                print(f"ERROR: 输出路径不能覆盖输入文件: {args.out}", file=sys.stderr)
                return 2
        try:
            parent = os.path.dirname(out_abs)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            with open(out_abs, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(output)
        except OSError as exc:
            print(f"ERROR: 写入失败: {exc}", file=sys.stderr)
            return 2
        print(f"报告已写入: {args.out}")
    else:
        sys.stdout.write(output)

    # ---- 退出码 ----
    if any(c.status == FAIL for c in required):
        return 1
    if args.strict and any(c.status == WARN for c in optional):
        return 1
    if any(f.startswith("config_warn") for f in flags) and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

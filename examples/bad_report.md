# 提交前自查审计报告 — GitHub Repository（示例：缺件提交）

- 目标目录：`examples/demo-bad`
- 清单来源：examples/demo-bad\challenge.json
- Rubric 来源：无（文件不存在: examples/demo-bad\rubric.json）

> 本报告只校验**文件是否存在、结构信号是否出现**，不判断内容的语义正确性。

## 总览

| 项 | 结果 |
|---|---|
| 必交项 | 1/4 PASS（25.0%） |
| 可选项 | 0/2 已具备 |
| 红旗 | 3 项触发 |

## 必交项勾选表

| 状态 | 要求 | 匹配模式 | 命中文件 |
|---|---|---|---|
| ✅ PASS | README.md | `README.md` | `README.md` |
| ❌ FAIL | *repo链接* | `*repo链接*` | — |
| ❌ FAIL | *AI日志* | `*AI日志*` | — |
| ❌ FAIL | *拿来说明* | `*拿来说明*` | — |

## 缺失清单

1. `*repo链接*` → 新建匹配 `*repo链接*` 的文件（建议命名 lsa_C5_…）.
2. `*AI日志*` → 新建匹配 `*AI日志*` 的文件（建议命名 lsa_C5_…）.
3. `*拿来说明*` → 新建匹配 `*拿来说明*` 的文件（建议命名 lsa_C5_…）.

## 可选项 / 加分项

| 状态 | 加分项 | 命中文件 |
|---|---|---|
| ⬜ 待补 | LICENSE | — |
| ⬜ 待补 | CONTRIBUTING.md | — |

## 红旗检查

- 🚩 missing_artifacts：存在未满足的必交项
- 🚩 no_ai_log：未发现 AI 使用记录
- 🚩 config_warn：文件不存在: examples/demo-bad\rubric.json

## 下一步（按优先级）

1. 补齐必交项 `*repo链接*`。
2. 补齐必交项 `*AI日志*`。
3. 补齐必交项 `*拿来说明*`。

---

_由 challenge_audit.py v1.0.0 生成 · 仅校验存在性与结构信号 · 输出不含主观评分_

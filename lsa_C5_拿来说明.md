# C5 拿来说明（提交版）

> 姓名：lsa ｜ 挑战：C5 ｜ 项目类型：自动化脚本 ｜ 日期：2026-11-20
>
> 本文件为提交文件命名规范 `姓名_C5_拿来说明.md` 要求的提交版；内容与仓库内 `ATTRIBUTION.md` 同源（下方为完整正文）。凡姓名一律用 lsa。

---

# 拿来说明（ATTRIBUTION.md）

> 作者：lsa ｜ 项目：challenge-audit ｜ 挑战：C5 GitHub Repository
>
> 本项目坚持「拿来主义」：站在已有的成熟规范与工具之上，明确标注每一处借鉴，**不假装凭空原创**。下表逐项说明「拿了什么 / 改了什么 / 为什么改」。

---

## 1. 借鉴来源总览

```text
[挑战方材料]
├── CHALLENGE.md          → 必交清单结构、README 10 节模板、检查清单
├── rubric.json           → 五维评分模型、3 类红旗
└── challenge.json        → required_deliverables 的逗号分隔格式
        ↓
[语言/平台官方文档]
├── Python argparse       → CLI 参数与退出码约定
├── Python pathlib        → 相对路径 POSIX 化（PurePosixPath.as_posix）
├── Python fnmatch/re     → glob → 正则的翻译规则
└── GitHub Actions 文档   → 多 OS × 多 Python 版本 CI 矩阵
        ↓
[作者自有项目（本人既往产出）]
├── audit_deliverables.py → 「检查表 + exit 1 作 CI 门」的设计
├── lsa_C4C_AAR.md        → AAR 的 7 节结构
└── MetaCal README        → 仓库 README 的「结构树 + 交付物对照」写法
        ↓
[本项目原创部分]
└── 通用 spec 驱动的自审计 + dogfood + JSON/strict 双输出
```

---

## 2. 逐项借鉴明细

| # | 来源 | 拿了什么 | 改了什么 | 为什么改 |
|---|------|---------|---------|---------|
| 1 | `CHALLENGE.md` §3.1 | 7 项「Repo 必须包含」清单 | 做成 `challenge.json` 的 `required_deliverables` 数组，支持通配符 | 把静态文字变成可执行的机器规则，便于复用与自动核对 |
| 2 | `CHALLENGE.md` §3.2 | README 10 节标准模板 | 逐节照搬顺序，并补「一句话描述/项目类型」标注 | 模板是挑战硬性要求，必须逐字对齐；补标注满足用户附加要求 |
| 3 | `CHALLENGE.md` §9 | `姓名_C5_*` 提交命名 | 改为 `lsa_C5_*`（姓名一律拼音 lsa） | 遵守用户「姓名一律 lsa，不得用汉字」的附加要求 |
| 4 | `rubric.json` | 五维（repoQuality/community/artifact/aiUsage/reflection）+ 3 红旗 | 转成结构化 `signals`（type/target），供工具做信号自评 | 让评分维度可被程序读取，输出「信号命中率」而非空泛自评 |
| 5 | `challenge.json`（EduSeed 导出） | `required_deliverables` 是逗号分隔字符串 | `parse_items()` 同时兼容字符串与数组 | 源数据两种格式都出现过，兼容才不会在读真实资料包时崩 |
| 6 | Python `pathlib` 官方文档 | `PurePosixPath.as_posix()` | 用于 `scan()` 统一路径分隔符 | 保证 Windows 上扫描结果仍是 `/` 分隔，跨平台一致 |
| 7 | Python `fnmatch` / `re` 文档 | glob 与正则的对应关系 | 自研 `glob_to_regex()`：区分 `*` 不跨 `/`、`**` 跨 `/`、basename 模式 | 标准库没有「含 `/` 与不含 `/` 语义不同」的现成函数，需定制 |
| 8 | Python `argparse` 官方示例 | 位置参数 + `--format` choices + `--version` | 加 `--strict` / `--no-timestamp` / `--out` | 支持 CI 门禁与可复现输出两个真实需求 |
| 9 | 作者项目 `audit_deliverables.py` | 「5 区块检查 + exit 1 作 CI 门」思路 | 改为 spec 驱动 + 可选 JSON 输出 | 原工具写死检查项，本项目做成通用武器 |
| 10 | 作者项目 `lsa_C4C_AAR.md` | AAR 的 7 节结构（目标/结果/保持/问题根因/失败清单/改进/总结） | 保留结构，内容换成 C5 项目 | 复用已验证的复盘框架，避免遗漏 rubric 要求的「根因/失败经验/改进」 |
| 11 | 作者项目 `MetaCal/README.md` | 「结构树 + 交付物对照表 + 质量双击命令」写法 | 精简后用于本 README | 该写法信息密度高、评审友好 |
| 12 | GitHub Actions 官方模板 | `matrix.os` × `matrix.python-version` | 设 3 OS × 3 版本，跑 unittest + 自审计 | 兑现「可复现性」——在多环境验证 5 分钟能跑 |

---

## 3. 本项目原创部分

| 原创点 | 说明 |
|--------|------|
| spec 驱动的通用自审计 | 同一工具既能审计任意资料包，也能审计自身（dogfood），不写死清单 |
| 内置默认清单 | 目标目录没有 `challenge.json` 时仍可运行并给 WARN，降低使用门槛 |
| `--format json --strict` 双输出 | 人读 Markdown、CI 读 JSON，一套逻辑两种消费者 |
| `--no-timestamp` 可复现输出 | 同一输入逐字节一致，便于纳入版本库做差异对比 |
| 红旗自动检测 | 把 rubric 的 3 类红旗（缺件 / 无 AI 日志 / one-shot）做成可判定规则 |
| 结构化 rubric 信号自评 | 用 type/target 描述信号，输出「命中 X/Y」而非主观打分 |

---

## 4. 边界声明与许可

- 本工具**只校验文件存在性与结构信号**，不判断内容语义是否正确（这是诚实的能力边界，已写入报告顶部）。
- 所有借鉴来源要么是挑战方公开材料、要么是 Python 标准库文档、要么是作者本人既往项目，**无第三方代码复制，无许可证冲突**。
- 本项目以 **MIT** 发布（见 `LICENSE`）；对上游材料的使用限于事实性清单与结构，未复制受版权保护的正文。

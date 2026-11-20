# 详细使用说明（usage.md）

## 命令格式

```bash
python challenge_audit.py [目录] [选项]
```

## 位置参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `目录` | 待审计的目录 | `.`（当前目录） |

## 选项

| 选项 | 说明 |
|------|------|
| `--config PATH` | 指定 `challenge.json` 路径（默认 `<目录>/challenge.json`） |
| `--rubric PATH` | 指定 `rubric.json` 路径（默认 `<目录>/rubric.json`） |
| `--out PATH` | 输出文件；不指定则打印到标准输出 |
| `--format {md,json}` | 输出格式（默认 `md`） |
| `--strict` | 加分项缺失（WARN）也视为失败，退出码 1 |
| `--exclude GLOB` | 追加排除模式，可重复；默认已排除 `.git`/`__pycache__`/`.venv`/`node_modules` 等 |
| `--no-timestamp` | 去掉生成时间，输出可逐字节复现 |
| `--version` | 打印版本号 |

## 清单文件格式（challenge.json）

```json
{
  "challenge_id": "C5",
  "title": "GitHub Repository",
  "required_deliverables": ["README.md", "*repo链接*", "*AI日志*", "*拿来说明*"],
  "optional_deliverables": ["LICENSE", ".github/ISSUE_TEMPLATE/"]
}
```

`required_deliverables` 与 `optional_deliverables` 支持**数组**或**逗号分隔字符串**两种格式（兼容 EduSeed 导出）。

### glob 规则

| 模式 | 含义 |
|------|------|
| `README.md` | 文件名为 `README.md`（任意目录，按 basename 匹配） |
| `*repo链接*` | 文件名包含 `repo链接` |
| `docs/*.md` | `docs/` 下一层的 `.md`（`*` 不跨 `/`） |
| `**/*.md` | 任意深度的 `.md`（含根目录，`**` 跨 `/`） |
| `.github/ISSUE_TEMPLATE/` | 该目录存在（以 `/` 结尾表示目录） |

## 评分维度文件格式（rubric.json）

```json
{
  "dimensions": [
    {"key": "repoQuality", "name": "仓库质量", "max": 25,
     "signals": [
       {"type": "file", "target": "README.md"},
       {"type": "regex", "target": "README.md", "pattern": "## 快速开始"},
       {"type": "count_min", "target": "examples/*.md", "min": 2},
       {"type": "prefix", "target": ".github/workflows/"}
     ]}
  ]
}
```

信号类型：

- `file`：文件存在
- `regex`：文件内容匹配正则
- `count_min`：匹配数量 ≥ `min`
- `prefix`：目录存在

EduSeed 原生的字符串信号（如 `"README专业"`）会做兜底关键词识别；识别不了的项标为「需人工核对」，不会误判为已达成。

## 退出码

| 码 | 含义 |
|:--:|------|
| 0 | 全部必交项 PASS（`--strict` 下还需无 WARN） |
| 1 | 存在 FAIL（或 `--strict` 下有 WARN / 配置告警） |
| 2 | 配置或 IO 错误（目录不存在、JSON 非法、输出覆盖输入） |

## 边界情况

| 情况 | 行为 |
|------|------|
| 目录不存在 | 打印错误，退出码 2 |
| 无 `challenge.json` | 用内置默认清单 + WARN，仍可运行 |
| JSON 含 BOM | 自动兼容 |
| JSON 非法 | 报告行:列，退出码 2 |
| 空目录 | 完成度 0%，全部列缺失，退出码 1 |
| 中文 / 空格路径 | 支持（路径统一 POSIX 化） |
| 符号链接环 | 不跟随（避免死循环） |
| `--out` 指向输入文件 | 拒绝覆盖，退出码 2 |

## CI 用法

```yaml
- run: python challenge_audit.py . --format json --strict --out audit.json
```

`--strict` 让加分项缺失也失败，适合作为「提交前必须全齐」的硬门禁。

## 能力边界（诚实声明）

本工具只校验**文件是否存在、结构信号是否出现**，**不判断内容的语义正确性**。例如它能确认 `AI_LOG.md` 存在且含时间戳，但不能判断日志内容是否真实、反思是否深刻——这部分仍需人工判断。

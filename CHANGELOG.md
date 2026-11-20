# Changelog

本项目所有重要变更记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/)。

## [1.0.0] - 2026-11-20

### Added
- 首个公开版本：零依赖、跨平台的 `challenge_audit.py`。
- `challenge.json` / `rubric.json` 驱动的清单与评分信号自评。
- Markdown / JSON 双输出，`--strict` CI 门禁，`--no-timestamp` 可复现输出。
- 红旗检测：`missing_artifacts` / `no_ai_log` / `one_shot_ai`。
- 23 个 unittest 用例；PASS / FAIL 两种真实示例报告；dogfood 自审计。
- 完整文档：README（10 节模板）、AI_LOG、ATTRIBUTION、AAR、docs/usage。
- 社区要素：CONTRIBUTING、CODE_OF_CONDUCT、issue / PR 模板、多环境 CI。

### Fixed
- `parse_items()` 兼容 EduSeed 导出的逗号分隔字符串清单。
- `load_json()` 兼容 UTF-8 BOM；Windows 控制台中文编码兜底。
- `scan()` 统一 POSIX 路径分隔符，跨平台匹配一致。

## [0.2.0] - 2026-11-20（内部）

### Added
- 结构化 rubric signals（file / regex / count_min / prefix）。
- 内置默认清单：目标目录无 `challenge.json` 时仍可运行并告警。

## [0.1.0] - 2026-11-20（内部）

### Added
- 主程序骨架、glob→正则翻译、基础 CLI。

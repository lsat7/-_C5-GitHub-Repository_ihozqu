# 贡献指南（CONTRIBUTING.md）

感谢你愿意改进 `challenge-audit`！无论是报 bug、提需求还是直接贡献代码，都欢迎。

## 开发环境

- Python 3.8+，无需安装第三方依赖。
- Fork 仓库 → 创建分支 → 修改 → 跑测试 → 提 PR。

```bash
git clone https://github.com/lsat7/-_C5-GitHub-Repository_ihozqu.git
cd -_C5-GitHub-Repository_ihozqu
python -m unittest discover -s tests -v        # 必须全绿
python challenge_audit.py examples/demo-good --no-timestamp   # 应为 4/4 PASS
python challenge_audit.py . --no-timestamp --format json      # 自审计应 0 红旗
```

## 提交 bug

用 `bug_report.yml` 模板新建 Issue，尽量给出：复现命令、实际输出、期望输出、Python 版本与操作系统。

## 提出功能建议

用 `feature_request.yml` 模板，说明使用场景与验收标准。能附上「希望的输入/输出示例」最好。

## 代码规范

- 仅用标准库；若确需第三方依赖，先在 Issue 中说明理由。
- 新增功能必须补 unittest，并保持 `python -m unittest discover -s tests` 全绿。
- 路径处理统一用 `/`；文本读写显式 `encoding="utf-8"`（读 JSON 用 `utf-8-sig`）。
- 提交信息用祈使句，如 `fix: 兼容逗号分隔清单`。

## PR 流程

1. 一个 PR 只做一件事。
2. 填写 PR 模板，勾选已跑过的验证命令。
3. 更新 `CHANGELOG.md`（在 Unreleased 或对应版本下加一行）。
4. 若改动影响输出格式，同步更新 `examples/*_report.md` 与 README 示例。

## 行为准则

参与本项目即表示你同意遵守 [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md)。

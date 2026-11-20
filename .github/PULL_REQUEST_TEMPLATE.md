# Pull Request

## 这个 PR 做了什么

<!-- 一句话说明 -->

## 相关 Issue

<!-- 例如 Closes #12 -->

## 改动类型

- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档改进
- [ ] 测试补充
- [ ] 其他

## 验证清单

- [ ] `python -m unittest discover -s tests` 全部通过
- [ ] `python challenge_audit.py examples/demo-good --no-timestamp` → 4/4 PASS，退出码 0
- [ ] `python challenge_audit.py examples/demo-bad --no-timestamp` → 1/4 FAIL，退出码 1
- [ ] `python challenge_audit.py . --no-timestamp --format json` → 0 红旗
- [ ] 已更新 `CHANGELOG.md`
- [ ] 若影响输出格式，已同步更新 `examples/*_report.md` 与 README 示例

## 补充说明

<!-- 任何需要 reviewer 知道的信息 -->

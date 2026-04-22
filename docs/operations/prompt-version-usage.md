# Prompt 版本变更指南

## 版本号位置

`server/prompts/registry.yaml` → `version` 字段

## 语义规则

| 变更类型 | 版本递增 | 示例 |
|----------|----------|------|
| 措辞修正，输出行为不变 | patch | 0.0.1 → 0.0.2 |
| 策略调整，输出行为有变化 | minor | 0.1.0 → 0.2.0 |
| 架构重构 / 新增 agent | major | 1.0.0 → 2.0.0 |

## 操作步骤

1. 编辑 `server/prompts/` 下对应 YAML 文件
2. 递增 `registry.yaml` 中的 `version`
3. 通过 Debug 接口验证：

```bash
curl -X POST http://localhost:8000/debug/prompt-preview \
  -H "x-debug-api-key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"reading_goal":"exam","reading_variant":"gaokao","agent_type":"vocabulary","include_instructions":true}'
```

4. 提交：

```bash
git add server/prompts/
git commit -m "feat(prompt): <简述变更> v0.0.1→v0.0.2"
```

## 回滚

```bash
git revert <commit-hash>
```

Git 即版本系统，无需在文件名或字段名中编码版本号。

# 数据库目录

## 目录结构

```
db/
├── migrations/
│   └── 0001_initial_schema.sql   # 全量初始 schema（19 张表）
├── reset_dev_keep_dict.sql       # 日常重置：仅清空业务表数据
└── reset_full_keep_dict.sql      # 完整重置：DROP 业务表后配合 0001 重建
```

## 表清单

### 业务表（16 张，重置时清空或删除）

| 域 | 表 | 说明 |
|---|---|---|
| 用户 | `users` | 用户主表 |
| 认证 | `user_identities` | 第三方登录映射 |
| 认证 | `user_sessions` | 会话管理 |
| 分析 | `analysis_records` | 文章分析记录 |
| 分析 | `analysis_results` | 分析结果（1:1 关联 record） |
| 分析 | `analysis_tasks` | 任务队列与并发控制 |
| 分析 | `analysis_task_events` | 任务事件日志 |
| 分析 | `analysis_audit_logs` | 审计日志 |
| 积分 | `user_credit_accounts` | 积分账户快照 |
| 积分 | `user_credit_ledger` | 积分流水 |
| 积分 | `anonymous_quotas` | 匿名试用额度 |
| 资产 | `favorite_records` | 收藏记录 |
| 资产 | `vocabulary_book` | 生词本 |
| 反馈 | `feedback` | 用户反馈 |
| 精读 | `daily_readers` | 每日精读文章 |
| 精读 | `pipeline_runs` | Pipeline 执行记录 |

### 词典表（3 张，重置时保留）

| 表 | 行数 | 大小 | 说明 |
|---|---|---|---|
| `dict_entries` | ~25 万 | ~536 MB | 词条详情（TECD3） |
| `dict_lookup_targets` | ~98 万 | ~457 MB | 查询映射索引 |
| `dict_redirects` | ~82 万 | ~255 MB | 重定向关系 |

词典三表合计约 **205 万行 / 1.25 GB**，重新导入需 20+ 分钟，且 `exam_tags` 字段需额外脚本标注，因此重置时必须保留。

## 三种操作场景

### 场景 A：日常开发 — 只清数据，不动结构

表结构没变，只想清空测试数据：

```bash
psql "$DATABASE_URL" -f db/reset_dev_keep_dict.sql
```

效果：TRUNCATE 16 张业务表，dict 三表数据不动。

### 场景 B：表结构变更 — 重建业务表，保留词典

修改了 0001 中的表定义后，需要重建表结构：

```bash
psql "$DATABASE_URL" -f db/reset_full_keep_dict.sql
psql "$DATABASE_URL" -f db/migrations/0001_initial_schema.sql
```

效果：第一步 DROP 16 张业务表，第二步重建全部 19 张表。dict 三表使用 `IF NOT EXISTS`，已存在时安全跳过。

### 场景 C：全新空库初始化

从零开始搭建开发环境：

```bash
psql "$DATABASE_URL" -f db/migrations/0001_initial_schema.sql
python scripts/import_tecd3.py
python scripts/backfill_phrases.py
```

## 词典数据保护规则

1. `reset_dev_keep_dict.sql` 和 `reset_full_keep_dict.sql` 均不会删除 dict 三表
2. `vocabulary_book.dict_entry_id` 使用 `ON DELETE SET NULL`，即使意外删除词条也不会级联丢失生词
3. dict 三表使用 BIGSERIAL 主键，与业务表 UUID 序列独立，重置业务表 `RESTART IDENTITY` 不影响 dict 序列
4. 如确需重建词典数据，必须先确认 `import_tecd3.py` + `exam_tags` 标注方案可用

## Migration 历史

当前 0001 是合并后的全量 schema，已包含以下历史 migration 的全部 DDL：

| 历史 Migration | 内容 | 合并方式 |
|---|---|---|
| 原 0001 | 15 张表 + 函数 + 触发器 + COMMENT | 基础 |
| 原 0002 | `feedback` 表 + `entry_type` 扩展 | 直接合入 |
| 原 0003 | `daily_readers` 表 | 直接合入 |
| 原 0004 | `daily_readers.original_text` 列 | 合入建表语句 |
| 原 0005 | 修复双重序列化 JSONB | 不纳入（一次性数据修复） |
| 原 0006 | `pipeline_runs` 表 | 直接合入 |

合并时的调整：
- `daily_readers` 建表时直接包含 `original_text` 列
- `user_credit_ledger.entry_type` CHECK 直接包含 `feedback_reward`
- `pipeline_runs` 去掉 `IF NOT EXISTS`
- `idx_daily_readers_source_url` 修正为 `idx_daily_readers_original_text_hash`
- dict 三表 `CREATE TABLE` 使用 `IF NOT EXISTS`，支持保留词典重建业务表

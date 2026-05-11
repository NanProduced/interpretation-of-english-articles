# 生词本复习功能实施计划

## 目标

第一版只做“记忆曲线提醒 + 卡片浏览 + 手动标记”，不做选择题、拼写题、释义匹配。

复习功能仍属于“我的生词本”二级入口，不新增底部 Tab，不改“我的”页信息架构。

## 设计资产

- `docs/uiux/vocabulary-review/assets/vocab-book-simplified.png`
- `docs/uiux/vocabulary-review/assets/review-context-card.png`
- `docs/uiux/vocabulary-review/assets/review-dictionary-card.png`
- `docs/uiux/vocabulary-review/assets/review-complete.png`

## 数据模型

后端已有字段：

- `mastery_status`
- `review_count`
- `last_reviewed_at`

本期新增复习调度字段建议放入 `payload_json.review`，避免先做数据库迁移：

```json
{
  "review": {
    "stage": 0,
    "next_review_at": "2026-05-12T00:00:00+08:00",
    "last_result": "known",
    "last_reviewed_at": "2026-05-11T16:30:00+08:00"
  }
}
```

后续如果数据量变大，再把 `next_review_at` 提升为数据库列。

## 复习算法

固定间隔即可：

| stage | 下次复习 |
|---:|---|
| 0 | 明天 |
| 1 | 3 天后 |
| 2 | 7 天后 |
| 3 | 14 天后 |
| 4 | 30 天后 |
| 5 | `mastered` |

动作：

- `已掌握`：`stage += 1`，更新 `next_review_at`，`review_count += 1`，`last_reviewed_at = now`。stage >= 5 时 `mastery_status = mastered`。
- `还不熟`：`stage = 0`，`next_review_at = 明天`，`review_count += 1`，`mastery_status = learning`。

## 后端任务

1. 扩展 `VocabularyPayload`，加入 `review` 结构。
2. 新增服务函数：
   - 获取待复习词条：按 `payload_json.review.next_review_at <= now` 过滤。
   - 提交复习结果：`known / unfamiliar`，更新 payload、`mastery_status`、`review_count`、`last_reviewed_at`。
3. 新增 API：
   - `GET /vocabulary/review/due?limit=20`
   - `POST /vocabulary/{vocab_id}/review`
4. `POST /vocabulary` 新增词时，如无 review payload，初始化 `stage=0`、`next_review_at=明天`。
5. 补单元测试：初始化、已掌握递进、还不熟回退、due 过滤。

## 前端任务

1. 扩展 `VocabEntry`：
   - `masteryStatus?: string`
   - `reviewStage?: number`
   - `nextReviewAt?: string`
   - `reviewCount?: number`
   - `lastReviewedAt?: string`
2. `vocabulary.client.ts` 增加：
   - `fetchDueVocabulary(limit)`
   - `submitVocabReview(vocabId, result)`
3. 改造 `packageA/vocab/index.tsx`：
   - 保留“我的生词本”入口现有路由。
   - 顶部显示今日待复习卡。
   - 主筛选只保留 `待复习 / 全部`。
   - 更多筛选收进右侧小图标入口，可先做轻量 bottom sheet 或暂缓。
4. 新增复习页面：
   - 建议路径：`packageA/vocab-review/index`
   - 语境/词典两个视图，优先 tab 实现；横滑作为增强。
   - 底部动作：`还不熟` / `已掌握`。
   - 完成页展示统计和下次复习。
5. 复用现有 `fetchDictEntry` 加载完整词典详情，不新增词典接口。

## 集成验收

- 新收藏的词会出现在待复习队列。
- 生词本页只显示 `待复习 / 全部`，移动端不过度拥挤。
- 今日复习卡片可以看来源语境，也可以切到词典详情。
- 点击 `已掌握` 后下次复习时间递进。
- 点击 `还不熟` 后明天继续提醒。
- 完成页统计与本次操作一致。
- 不影响结果页 saved-vocab overlay、WordPopup 保存状态和生词详情页查看原文。

"""
艾宾浩斯遗忘曲线复习系统服务。

实现 SM-2 算法（SuperMemo 2 algorithm），这是基于艾宾浩斯遗忘曲线
的科学复习调度算法，被 Anki、SuperMemo 等著名记忆软件采用。

SM-2 算法核心逻辑：
- 易度因子 (Ease Factor, EF): 表示单词的难易程度，默认 2.5，最低 1.3
- 复习间隔 (Interval, I): 两次复习之间的天数
- 连续成功次数 (Repetitions): 连续成功复习的次数

算法流程：
1. 第一次复习: Interval = 1 天
2. 第二次复习: Interval = 6 天
3. 后续复习: 
   - 如果 quality >= 3 (记住了):
     * Interval = Interval * EF
     * EF = EF + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
     * Repetitions += 1
   - 如果 quality < 3 (忘记了):
     * Repetitions = 0（重新开始）
     * Interval = 1 天
   - EF 不能低于 1.3

质量评分 (Quality, 0-5):
- 0: 完全忘记 (Complete Blackout)
- 1: 几乎忘记 (Wrong Response)
- 2: 模糊记得 (Wrong Response, On The Tip Of The Tongue)
- 3: 记住了 (Correct Response, With Serious Difficulty)
- 4: 熟练掌握 (Correct Response, With Some Hesitation)
- 5: 完全掌握 (Perfect Response)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.database import connection as db_connection

SM2_DEFAULT_EASE_FACTOR = 2.5
SM2_MIN_EASE_FACTOR = 1.3
SM2_FIRST_INTERVAL = 1
SM2_SECOND_INTERVAL = 6


def calculate_next_review(
    current_ease_factor: float,
    current_interval: int,
    current_repetitions: int,
    quality: int,
) -> tuple[float, int, int]:
    """
    根据 SM-2 算法计算下一次复习参数。

    Args:
        current_ease_factor: 当前易度因子
        current_interval: 当前复习间隔（天）
        current_repetitions: 当前连续成功次数
        quality: 复习质量评分 (0-5)

    Returns:
        (new_ease_factor, new_interval, new_repetitions)
    """
    if quality >= 3:
        if current_repetitions == 0:
            new_interval = SM2_FIRST_INTERVAL
        elif current_repetitions == 1:
            new_interval = SM2_SECOND_INTERVAL
        else:
            new_interval = round(current_interval * current_ease_factor)

        delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        new_ease_factor = current_ease_factor + delta
        new_ease_factor = max(new_ease_factor, SM2_MIN_EASE_FACTOR)

        new_repetitions = current_repetitions + 1
    else:
        new_repetitions = 0
        new_interval = SM2_FIRST_INTERVAL
        new_ease_factor = current_ease_factor

    return round(new_ease_factor, 3), new_interval, new_repetitions


def determine_mastery_status(
    repetitions: int,
    ease_factor: float,
    quality: int,
) -> str:
    """
    根据复习情况确定掌握状态。

    状态转换逻辑：
    - new: 从未复习过 (repetitions = 0)
    - learning: 正在学习中 (repetitions < 3 或 quality < 4)
    - review: 需要复习
    - mastered: 已掌握 (repetitions >= 5 且 ease_factor >= 2.5)
    - archived: 已归档（需手动设置）

    Args:
        repetitions: 连续成功复习次数
        ease_factor: 易度因子
        quality: 本次复习质量

    Returns:
        mastery_status 字符串
    """
    if repetitions >= 5 and ease_factor >= 2.5:
        return "mastered"
    elif repetitions >= 3:
        return "learning"
    elif quality < 3:
        return "learning"
    elif repetitions == 0:
        return "new"
    else:
        return "learning"


async def submit_review(
    user_id: UUID,
    vocab_id: UUID,
    quality: int,
) -> dict[str, Any]:
    """
    提交复习结果，根据 SM-2 算法更新复习调度。

    Args:
        user_id: 用户 ID
        vocab_id: 生词记录 ID
        quality: 复习质量评分 (0-5)

    Returns:
        包含更新后状态的字典
    """
    if quality < 0 or quality > 5:
        raise ValueError("Quality must be between 0 and 5")

    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id, ease_factor, review_interval, repetitions, 
                       mastery_status, review_count
                FROM vocabulary_book
                WHERE id = $1 AND user_id = $2
                """,
                vocab_id,
                user_id,
            )

            if row is None:
                raise ValueError("Vocabulary entry not found")

            current_ease = float(row["ease_factor"])
            current_interval = row["review_interval"]
            current_repetitions = row["repetitions"]
            current_review_count = row["review_count"]

            new_ease, new_interval, new_repetitions = calculate_next_review(
                current_ease_factor=current_ease,
                current_interval=current_interval,
                current_repetitions=current_repetitions,
                quality=quality,
            )

            new_mastery = determine_mastery_status(
                repetitions=new_repetitions,
                ease_factor=new_ease,
                quality=quality,
            )

            now = datetime.now(UTC)
            next_review_at = now + timedelta(days=new_interval)

            await conn.execute(
                """
                UPDATE vocabulary_book
                SET 
                    ease_factor = $1,
                    review_interval = $2,
                    repetitions = $3,
                    mastery_status = $4,
                    review_count = $5,
                    last_reviewed_at = $6,
                    next_review_at = $7,
                    updated_at = $6
                WHERE id = $8 AND user_id = $9
                """,
                new_ease,
                new_interval,
                new_repetitions,
                new_mastery,
                current_review_count + 1,
                now,
                next_review_at,
                vocab_id,
                user_id,
            )

            return {
                "vocab_id": vocab_id,
                "success": True,
                "next_review_at": next_review_at,
                "new_ease_factor": new_ease,
                "new_interval": new_interval,
                "new_repetitions": new_repetitions,
                "new_mastery_status": new_mastery,
                "quality": quality,
                "message": _get_review_message(quality, new_repetitions),
            }


def _get_review_message(quality: int, repetitions: int) -> str:
    """根据复习质量生成提示消息。"""
    if quality >= 4:
        if repetitions >= 5:
            return "太棒了！这个单词已经完全掌握了！"
        elif repetitions >= 3:
            return "记得很好，继续保持！"
        else:
            return "不错，继续复习巩固！"
    elif quality == 3:
        return "勉强记住了，下次要多注意哦"
    elif quality == 2:
        return "有点模糊，需要加强复习"
    elif quality == 1:
        return "几乎忘记了，明天重新开始"
    else:
        return "完全忘记了，需要重新学习"


async def get_review_stats(user_id: UUID) -> dict[str, Any]:
    """
    获取用户的复习统计数据。

    统计内容包括：
    - 总生词数
    - 今日待复习数
    - 逾期未复习数
    - 各状态数量

    Args:
        user_id: 用户 ID

    Returns:
        统计数据字典
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM vocabulary_book WHERE user_id = $1",
            user_id,
        )

        due_today = await conn.fetchval(
            """
            SELECT COUNT(*) FROM vocabulary_book 
            WHERE user_id = $1 
              AND mastery_status IN ('new', 'learning', 'review')
              AND next_review_at >= $2 
              AND next_review_at < $3
            """,
            user_id,
            today_start,
            today_end,
        )

        overdue = await conn.fetchval(
            """
            SELECT COUNT(*) FROM vocabulary_book 
            WHERE user_id = $1 
              AND mastery_status IN ('new', 'learning', 'review')
              AND next_review_at < $2
            """,
            user_id,
            today_start,
        )

        new_words = await conn.fetchval(
            """
            SELECT COUNT(*) FROM vocabulary_book 
            WHERE user_id = $1 AND mastery_status = 'new'
            """,
            user_id,
        )

        learning = await conn.fetchval(
            """
            SELECT COUNT(*) FROM vocabulary_book 
            WHERE user_id = $1 AND mastery_status = 'learning'
            """,
            user_id,
        )

        mastered = await conn.fetchval(
            """
            SELECT COUNT(*) FROM vocabulary_book 
            WHERE user_id = $1 AND mastery_status = 'mastered'
            """,
            user_id,
        )

        return {
            "total_vocab": int(total) if total else 0,
            "due_today": int(due_today) if due_today else 0,
            "overdue": int(overdue) if overdue else 0,
            "new_words": int(new_words) if new_words else 0,
            "learning": int(learning) if learning else 0,
            "mastered": int(mastered) if mastered else 0,
        }


async def get_due_vocabulary(
    user_id: UUID,
    due_type: str = "today",
    limit: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """
    获取待复习的单词列表。

    Args:
        user_id: 用户 ID
        due_type: 待复习类型: 'today'（今日）, 'overdue'（逾期）, 'new'（新词）
        limit: 返回数量限制

    Returns:
        (单词列表, 总数)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    async with pool.acquire() as conn:
        base_query = """
            SELECT 
                v.id, v.lemma, v.display_word, v.phonetic, v.part_of_speech,
                v.short_meaning, v.mastery_status, v.repetitions, v.ease_factor,
                v.review_interval, v.next_review_at, v.source_sentence,
                v.meanings_json, v.payload_json
            FROM vocabulary_book v
            WHERE v.user_id = $1
        """

        count_query = """
            SELECT COUNT(*) FROM vocabulary_book v
            WHERE v.user_id = $1
        """

        if due_type == "today":
            condition = """
                AND v.mastery_status IN ('new', 'learning', 'review')
                AND v.next_review_at >= $2 
                AND v.next_review_at < $3
            """
            order_by = "ORDER BY v.next_review_at ASC, v.created_at ASC"
            query_params = [user_id, today_start, today_end]
        elif due_type == "overdue":
            condition = """
                AND v.mastery_status IN ('new', 'learning', 'review')
                AND v.next_review_at < $2
            """
            order_by = "ORDER BY v.next_review_at ASC"
            query_params = [user_id, today_start]
        elif due_type == "new":
            condition = """
                AND v.mastery_status = 'new'
            """
            order_by = "ORDER BY v.created_at ASC"
            query_params = [user_id]
        else:
            raise ValueError(f"Invalid due_type: {due_type}")

        full_query = base_query + condition + " " + order_by + " LIMIT $" + str(len(query_params) + 1)
        query_params.append(limit)

        full_count_query = count_query + condition

        total = await conn.fetchval(full_count_query, *query_params[:-1])

        rows = await conn.fetch(full_query, *query_params)

        items = []
        for row in rows:
            item = dict(row)
            payload = item.get("payload_json")
            if payload and "source_refs" in payload:
                item["source_refs"] = payload["source_refs"]
            items.append(item)

        return items, int(total) if total else 0

"""
Feedback Service.

Handles CRUD operations for feedbacks table.
用于收集用户反馈，为后续 RAG 的 few-shot 注入做准备。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection


def _ensure_jsonb(row: dict | None) -> dict | None:
    """Ensure JSONB columns in a row are dictionaries."""
    if row is None:
        return None
    jsonb_columns = {"context_json", "client_metadata_json"}
    for col in jsonb_columns:
        if col in row and isinstance(row[col], str):
            try:
                row[col] = json.loads(row[col])
            except (json.JSONDecodeError, TypeError):
                row[col] = {}
    return row


async def create_feedback(
    user_id: UUID,
    feedback_type: str,
    satisfaction: bool | None = None,
    category: str | None = None,
    detail_text: str | None = None,
    analysis_record_id: UUID | None = None,
    context_json: dict[str, Any] | None = None,
    client_metadata_json: dict[str, Any] | None = None,
) -> UUID:
    """
    创建一条新的用户反馈记录。

    Args:
        user_id: 提交反馈的用户 ID
        feedback_type: 反馈类型
        satisfaction: 是否满意
        category: 反馈分类
        detail_text: 用户输入的详细理由
        analysis_record_id: 关联的分析记录 ID
        context_json: 上下文数据
        client_metadata_json: 客户端元数据

    Returns:
        新创建的反馈记录 ID
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO feedbacks (
                user_id, feedback_type, satisfaction, category, detail_text,
                analysis_record_id, context_json, client_metadata_json, status,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, 'pending', $9, $9)
            RETURNING id
            """,
            user_id,
            feedback_type,
            satisfaction,
            category,
            detail_text,
            analysis_record_id,
            json.dumps(context_json or {}, ensure_ascii=False),
            json.dumps(client_metadata_json or {}, ensure_ascii=False),
            now,
        )
        assert row is not None
        return UUID(str(row["id"]))


async def get_feedback_by_id(
    feedback_id: UUID,
    user_id: UUID | None = None,
) -> dict | None:
    """
    根据 ID 获取单条反馈记录。

    Args:
        feedback_id: 反馈记录 ID
        user_id: 用户 ID（可选，用于权限校验）

    Returns:
        反馈记录字典或 None
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    query = """
        SELECT id, user_id, feedback_type, satisfaction, category, detail_text,
               analysis_record_id, context_json, client_metadata_json, status,
               admin_note, created_at, updated_at
        FROM feedbacks
        WHERE id = $1
    """
    params: list[Any] = [feedback_id]

    if user_id is not None:
        query += " AND user_id = $2"
        params.append(user_id)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if row is None:
            return None
        return _ensure_jsonb(dict(row))


async def list_feedbacks(
    user_id: UUID,
    page: int = 1,
    limit: int = 20,
    feedback_type: str | None = None,
    satisfaction: bool | None = None,
    category: str | None = None,
    status: str | None = None,
) -> tuple[list[dict], int]:
    """
    获取用户的反馈列表（分页）。

    Args:
        user_id: 用户 ID
        page: 页码（从 1 开始）
        limit: 每页数量
        feedback_type: 筛选：反馈类型
        satisfaction: 筛选：满意度
        category: 筛选：反馈分类
        status: 筛选：处理状态

    Returns:
        (反馈列表, 总数量)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    offset = (page - 1) * limit

    where_conditions = ["user_id = $1"]
    params: list[Any] = [user_id]
    param_index = 2

    if feedback_type is not None:
        where_conditions.append(f"feedback_type = ${param_index}")
        params.append(feedback_type)
        param_index += 1

    if satisfaction is not None:
        where_conditions.append(f"satisfaction = ${param_index}")
        params.append(satisfaction)
        param_index += 1

    if category is not None:
        where_conditions.append(f"category = ${param_index}")
        params.append(category)
        param_index += 1

    if status is not None:
        where_conditions.append(f"status = ${param_index}")
        params.append(status)
        param_index += 1

    where_clause = " AND ".join(where_conditions)

    base_query = f"""
        SELECT id, user_id, feedback_type, satisfaction, category, detail_text,
               analysis_record_id, context_json, client_metadata_json, status,
               admin_note, created_at, updated_at
        FROM feedbacks
        WHERE {where_clause}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"{base_query} ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}",
            *params,
            limit,
            offset,
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM feedbacks WHERE {where_clause}",
            *params,
        )
        return [_ensure_jsonb(dict(row)) for row in rows], int(total)


async def count_feedbacks(
    user_id: UUID,
    feedback_type: str | None = None,
    satisfaction: bool | None = None,
) -> dict[str, int]:
    """
    统计用户的反馈数量（用于前端决策是否弹出反馈）。

    Args:
        user_id: 用户 ID
        feedback_type: 反馈类型筛选（可选）
        satisfaction: 满意度筛选（可选）

    Returns:
        包含统计信息的字典
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    where_conditions = ["user_id = $1"]
    params: list[Any] = [user_id]
    param_index = 2

    if feedback_type is not None:
        where_conditions.append(f"feedback_type = ${param_index}")
        params.append(feedback_type)
        param_index += 1

    if satisfaction is not None:
        where_conditions.append(f"satisfaction = ${param_index}")
        params.append(satisfaction)
        param_index += 1

    where_clause = " AND ".join(where_conditions)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM feedbacks WHERE {where_clause}",
            *params,
        )
        return {"total": int(total)}


async def update_feedback_status(
    feedback_id: UUID,
    user_id: UUID,
    status: str,
    admin_note: str | None = None,
) -> dict | None:
    """
    更新反馈记录的处理状态（仅供管理员/内部使用）。

    Args:
        feedback_id: 反馈记录 ID
        user_id: 用户 ID（用于权限校验）
        status: 新的状态
        admin_note: 管理员备注（可选）

    Returns:
        更新后的反馈记录或 None
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)

    async with pool.acquire() as conn:
        async with conn.transaction():
            update_fields = ["status = $1", "updated_at = $2"]
            params: list[Any] = [status, now, feedback_id, user_id]
            param_index = 5

            if admin_note is not None:
                update_fields.append(f"admin_note = ${param_index}")
                params.append(admin_note)
                param_index += 1

            result = await conn.execute(
                f"""
                UPDATE feedbacks
                SET {', '.join(update_fields)}
                WHERE id = $3 AND user_id = $4
                """,
                *params,
            )

            if "UPDATE 1" not in result:
                return None

        return await get_feedback_by_id(feedback_id, user_id)


async def should_trigger_feedback_popup(
    user_id: UUID,
    source_text_length: int,
    processing_ms: int | None = None,
    user_facing_state: str | None = None,
) -> bool:
    """
    决策是否应该弹出结果页反馈询问。

    规则：
    1. 文本字符数 > 300 且用户最近 3 次没有提交过相同类型的反馈
    2. 响应时间不正常（> 60 秒）
    3. 结果状态为 degraded_light 或 degraded_heavy（降级状态）

    同时限制：同一用户在 24 小时内最多弹出 3 次结果页反馈

    Args:
        user_id: 用户 ID
        source_text_length: 源文本字符数
        processing_ms: 处理耗时（毫秒）
        user_facing_state: 结果状态

    Returns:
        是否应该弹出反馈
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    should_trigger = False

    # 规则 1: 文本字符数 > 300
    if source_text_length > 300:
        should_trigger = True

    # 规则 2: 响应时间不正常（> 60 秒）
    if processing_ms is not None and processing_ms > 60000:
        should_trigger = True

    # 规则 3: 降级状态
    if user_facing_state in ["degraded_light", "degraded_heavy"]:
        should_trigger = True

    if not should_trigger:
        return False

    # 限制条件：检查用户最近 24 小时内的结果页反馈数量
    async with pool.acquire() as conn:
        recent_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM feedbacks
            WHERE user_id = $1
              AND feedback_type = 'result_overall'
              AND created_at >= NOW() - INTERVAL '24 hours'
            """,
            user_id,
        )

        # 24 小时内最多弹出 3 次
        if int(recent_count) >= 3:
            return False

    return True

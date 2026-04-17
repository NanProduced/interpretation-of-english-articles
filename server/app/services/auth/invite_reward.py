"""
邀请奖励服务。

处理邀请关系验证、奖励发放和防刷逻辑。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection

logger = logging.getLogger(__name__)

INVITE_REWARD_POINTS = 300
MAX_INVITE_COUNT = 10


class InviteRewardError(Exception):
    """邀请奖励错误"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


async def apply_invite_reward(
    invitee_id: UUID,
    inviter_id: str,
) -> dict[str, Any]:
    """
    应用邀请奖励。

    执行以下检查和操作：
    1. 验证 inviter_id 是有效的 UUID
    2. 检查 inviter_id 是否存在且不是 invitee_id（防自邀）
    3. 检查 invitee_id 是否已经有邀请者（防重复）
    4. 检查 inviter_id 的邀请数量是否已达上限（防刷）
    5. 所有检查通过后，在事务中：
       - 写入 user_invites 记录
       - 更新 users.inviter_id
       - 更新 inviter 的 successful_invite_count
       - 给 inviter 添加 bonus_points
       - 写入积分流水

    Args:
        invitee_id: 被邀请者用户ID
        inviter_id: 邀请者用户ID（字符串形式）

    Returns:
        {
            "applied": bool,  # 奖励是否成功发放
            "reward_points": int,  # 发放的积分数
            "reason": str | None,  # 未发放的原因
        }
    """
    if db_connection.DB_POOL is None:
        raise RuntimeError("Database pool not initialized")

    try:
        inviter_uuid = UUID(inviter_id)
    except ValueError:
        logger.warning("Invalid inviter_id format: %s", inviter_id)
        return {
            "applied": False,
            "reward_points": 0,
            "reason": "invalid_inviter_id",
        }

    if inviter_uuid == invitee_id:
        logger.warning("Self-invite attempt: user %s", invitee_id)
        return {
            "applied": False,
            "reward_points": 0,
            "reason": "self_invite",
        }

    async with db_connection.DB_POOL.acquire() as conn:
        async with conn.transaction():
            inviter_row = await conn.fetchrow(
                """
                SELECT id, successful_invite_count FROM users WHERE id = $1
                FOR UPDATE
                """,
                inviter_uuid,
            )
            if inviter_row is None:
                logger.warning("Inviter not found: %s", inviter_uuid)
                return {
                    "applied": False,
                    "reward_points": 0,
                    "reason": "inviter_not_found",
                }

            invitee_row = await conn.fetchrow(
                """
                SELECT id, inviter_id FROM users WHERE id = $1
                FOR UPDATE
                """,
                invitee_id,
            )
            if invitee_row is None:
                logger.warning("Invitee not found: %s", invitee_id)
                return {
                    "applied": False,
                    "reward_points": 0,
                    "reason": "invitee_not_found",
                }

            if invitee_row["inviter_id"] is not None:
                logger.warning(
                    "Invitee already has an inviter: %s -> %s",
                    invitee_id,
                    invitee_row["inviter_id"],
                )
                return {
                    "applied": False,
                    "reward_points": 0,
                    "reason": "already_has_inviter",
                }

            current_invite_count = inviter_row["successful_invite_count"] or 0
            if current_invite_count >= MAX_INVITE_COUNT:
                logger.warning(
                    "Inviter has reached max invite count: %s (count=%s)",
                    inviter_uuid,
                    current_invite_count,
                )
                return {
                    "applied": False,
                    "reward_points": 0,
                    "reason": "max_invite_count_reached",
                }

            now = datetime.now(timezone.utc)

            await conn.execute(
                """
                INSERT INTO user_invites
                    (inviter_id, invitee_id, reward_points, reward_applied, reward_applied_at, created_at)
                VALUES ($1, $2, $3, TRUE, $4, $5)
                """,
                inviter_uuid,
                invitee_id,
                INVITE_REWARD_POINTS,
                now,
                now,
            )

            await conn.execute(
                """
                UPDATE users
                SET inviter_id = $2, updated_at = $3
                WHERE id = $1
                """,
                invitee_id,
                inviter_uuid,
                now,
            )

            await conn.execute(
                """
                UPDATE users
                SET successful_invite_count = successful_invite_count + 1, updated_at = $2
                WHERE id = $1
                """,
                inviter_uuid,
                now,
            )

            credit_row = await conn.fetchrow(
                """
                SELECT user_id, bonus_points FROM user_credit_accounts
                WHERE user_id = $1
                FOR UPDATE
                """,
                inviter_uuid,
            )

            if credit_row is None:
                await conn.execute(
                    """
                    INSERT INTO user_credit_accounts
                        (user_id, bonus_points, created_at, updated_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    inviter_uuid,
                    INVITE_REWARD_POINTS,
                    now,
                    now,
                )
                new_bonus = INVITE_REWARD_POINTS
            else:
                new_bonus = (credit_row["bonus_points"] or 0) + INVITE_REWARD_POINTS
                await conn.execute(
                    """
                    UPDATE user_credit_accounts
                    SET bonus_points = $2, updated_at = $3
                    WHERE user_id = $1
                    """,
                    inviter_uuid,
                    new_bonus,
                    now,
                )

            daily_remaining = await conn.fetchval(
                """
                SELECT (daily_free_points - daily_used_points) AS remaining
                FROM user_credit_accounts
                WHERE user_id = $1
                """,
                inviter_uuid,
            )
            balance_after = (daily_remaining or 0) + new_bonus

            await conn.execute(
                """
                INSERT INTO user_credit_ledger
                    (user_id, entry_type, points, bucket_type, balance_after, metadata_json, created_at)
                VALUES ($1, 'bonus_grant', $2, 'bonus', $3, $4, $5)
                """,
                inviter_uuid,
                INVITE_REWARD_POINTS,
                balance_after,
                '{"invite_reward": true, "invitee_id": "' + str(invitee_id) + '"}',
                now,
            )

            logger.info(
                "Invite reward applied: inviter=%s, invitee=%s, points=%s",
                inviter_uuid,
                invitee_id,
                INVITE_REWARD_POINTS,
            )

            return {
                "applied": True,
                "reward_points": INVITE_REWARD_POINTS,
                "reason": None,
            }


async def get_successful_invite_count(user_id: UUID) -> int:
    """获取用户成功邀请的人数"""
    if db_connection.DB_POOL is None:
        raise RuntimeError("Database pool not initialized")

    async with db_connection.DB_POOL.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT successful_invite_count FROM users WHERE id = $1
            """,
            user_id,
        )
        return count or 0

"""
User Quota API.

Provides endpoints for checking user credit/quota information.
Supports both authenticated users (by user_id) and anonymous/guest users (by anonymous_id).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.analysis.credit_service import ensure_credit_account, get_quota_info
from app.services.auth.dependencies import AuthUserDep, OptionalAuthUserDep

logger = getLogger("app.api")

router = APIRouter(prefix="/me", tags=["user"])

ANONYMOUS_DAILY_TRIAL_LIMIT = 3


ENTRY_TYPE_DESCRIPTIONS: dict[str, str] = {
    "analysis_deduct": "分析扣减",
    "feedback_reward": "反馈奖励 · 你的反馈已被采纳",
    "daily_grant": "每日常规额度刷新",
    "bonus_grant": "奖励积分到账",
    "refund": "分析失败 · 积分退回",
    "manual_adjust": "管理员调整",
}


class QuotaResponse(BaseModel):
    daily_free_points: int
    daily_used_points: int
    bonus_points: int
    remaining_points: int


class AnonymousQuotaResponse(BaseModel):
    remaining_trials: int
    max_trials_per_day: int
    reset_at: str


class QuotaCheckRequest(BaseModel):
    anonymous_id: str | None = None


class QuotaCheckResponse(BaseModel):
    allowed: bool
    remaining: int
    reset_at: str
    quota_type: str


class LedgerEntryResponse(BaseModel):
    id: str
    entry_type: str
    points: int
    bucket_type: str
    balance_after: int
    description: str
    article_title: str | None
    created_at: datetime


class LedgerListResponse(BaseModel):
    items: list[LedgerEntryResponse]
    cursor: str | None
    has_more: bool


@router.get("/quota", response_model=QuotaResponse)
async def get_user_quota(
    current_user: AuthUserDep,
) -> QuotaResponse:
    """
    Get current user's quota information.

    Returns daily free points, used points, bonus points, and remaining total.
    Performs lazy daily reset if needed.
    """
    try:
        user_id = UUID(current_user.user_id)
        await ensure_credit_account(user_id)
        info = await get_quota_info(user_id)
        return QuotaResponse(**info)
    except Exception as e:
        logger.error("get_user_quota failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/quota/anonymous", response_model=AnonymousQuotaResponse)
async def get_anonymous_quota(
    anonymous_id: str,
) -> AnonymousQuotaResponse:
    """
    Get anonymous/guest user's remaining trial quota.

    Uses device-generated anonymous_id stored locally.
    Resets daily trial count at midnight.
    """
    from app.database import connection as db_connection

    if db_connection.DB_POOL is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    today = date.today()
    reset_at = datetime.combine(today, datetime.min.time()).astimezone(timezone.utc).isoformat()

    async with db_connection.DB_POOL.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT trial_count, last_trial_at FROM anonymous_quotas
            WHERE anonymous_id = $1
            """,
            anonymous_id,
        )

        if row is None:
            # New anonymous user
            return AnonymousQuotaResponse(
                remaining_trials=ANONYMOUS_DAILY_TRIAL_LIMIT,
                max_trials_per_day=ANONYMOUS_DAILY_TRIAL_LIMIT,
                reset_at=reset_at,
            )

        trial_count = row["trial_count"]
        last_trial = row["last_trial_at"]

        # Reset if new day
        if last_trial < today:
            return AnonymousQuotaResponse(
                remaining_trials=ANONYMOUS_DAILY_TRIAL_LIMIT,
                max_trials_per_day=ANONYMOUS_DAILY_TRIAL_LIMIT,
                reset_at=reset_at,
            )

        remaining = max(ANONYMOUS_DAILY_TRIAL_LIMIT - trial_count, 0)
        return AnonymousQuotaResponse(
            remaining_trials=remaining,
            max_trials_per_day=ANONYMOUS_DAILY_TRIAL_LIMIT,
            reset_at=reset_at,
        )


@router.post("/quota/check", response_model=QuotaCheckResponse)
async def check_quota(
    current_user: OptionalAuthUserDep = None,
    body: QuotaCheckRequest | None = None,
) -> QuotaCheckResponse:
    """
    Check if a request is allowed under quota limits.

    Authenticated users: checks their credit account (daily_free + bonus).
    Anonymous users: checks their anonymous trial count.

    Either pass current_user (from auth header) OR anonymous_id in body.
    Prefer authenticated users when both are available.
    """
    # Authenticated user path
    if current_user is not None:
        try:
            user_id = UUID(current_user.user_id)
            await ensure_credit_account(user_id)
            info = await get_quota_info(user_id)
            return QuotaCheckResponse(
                allowed=info["remaining_points"] > 0,
                remaining=info["remaining_points"],
                reset_at=_get_next_reset_iso(),
                quota_type="authenticated",
            )
        except Exception as e:
            logger.error("check_quota authenticated failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e

    # Anonymous user path
    if body is None or not body.anonymous_id:
        raise HTTPException(status_code=400, detail="anonymous_id required for guest users")

    anonymous_id = body.anonymous_id

    try:
        remaining, reset_at = await _check_anonymous_quota(anonymous_id)
        return QuotaCheckResponse(
            allowed=remaining > 0,
            remaining=remaining,
            reset_at=reset_at,
            quota_type="anonymous",
        )
    except Exception as e:
        logger.error("check_quota anonymous failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _check_anonymous_quota(anonymous_id: str) -> tuple[int, str]:
    """Check and increment anonymous user trial count. Returns (remaining, reset_at_iso)."""
    from app.database import connection as db_connection

    if db_connection.DB_POOL is None:
        raise RuntimeError("Database pool not initialized")

    today = date.today()
    reset_at = datetime.combine(today, datetime.min.time()).astimezone(timezone.utc).isoformat()

    async with db_connection.DB_POOL.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT trial_count, last_trial_at FROM anonymous_quotas
                WHERE anonymous_id = $1
                FOR UPDATE
                """,
                anonymous_id,
            )

            if row is None:
                # First trial — create record
                await conn.execute(
                    """
                    INSERT INTO anonymous_quotas (anonymous_id, trial_count, last_trial_at)
                    VALUES ($1, 1, $2)
                    """,
                    anonymous_id,
                    today,
                )
                return ANONYMOUS_DAILY_TRIAL_LIMIT - 1, reset_at

            trial_count = row["trial_count"]
            last_trial = row["last_trial_at"]

            # Reset if new day
            if last_trial < today:
                await conn.execute(
                    """
                    UPDATE anonymous_quotas
                    SET trial_count = 1, last_trial_at = $2, updated_at = NOW()
                    WHERE anonymous_id = $1
                    """,
                    anonymous_id,
                    today,
                )
                return ANONYMOUS_DAILY_TRIAL_LIMIT - 1, reset_at

            if trial_count >= ANONYMOUS_DAILY_TRIAL_LIMIT:
                # Exhausted
                return 0, reset_at

            # Increment
            await conn.execute(
                """
                UPDATE anonymous_quotas
                SET trial_count = trial_count + 1, updated_at = NOW()
                WHERE anonymous_id = $1
                """,
                anonymous_id,
            )

            remaining = ANONYMOUS_DAILY_TRIAL_LIMIT - trial_count - 1
            return remaining, reset_at


def _get_next_reset_iso() -> str:
    """Get ISO datetime for next midnight UTC (next reset)."""
    tomorrow = date.today()
    return datetime.combine(tomorrow, datetime.min.time()).astimezone(timezone.utc).isoformat()


@router.get("/credit/ledger", response_model=LedgerListResponse)
async def get_credit_ledger(
    current_user: AuthUserDep,
    cursor: str | None = None,
    limit: int = 20,
) -> LedgerListResponse:
    from fastapi import Query
    from app.database import connection as db_connection

    user_id = UUID(current_user.user_id)
    pool = db_connection.DB_POOL
    if pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    limit_val = min(limit, 100)
    params: list = [user_id]
    where_clauses = ["user_id = $1"]

    if cursor:
        params.append(UUID(cursor))
        where_clauses.append(f"id < ${len(params)}")

    params.append(limit_val + 1)
    query_limit = f"${len(params)}"
    where_sql = " AND ".join(where_clauses)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT l.id, l.entry_type, l.points, l.bucket_type,
                   l.balance_after, l.metadata_json, l.created_at,
                   l.task_id,
                   r.title AS article_title
            FROM user_credit_ledger l
            LEFT JOIN analysis_tasks t ON l.task_id = t.id
            LEFT JOIN analysis_records r ON t.analysis_record_id = r.id
            WHERE {where_sql}
            ORDER BY l.created_at DESC
            LIMIT {query_limit}
            """,
            *params,
        )

    items = []
    for row in rows[:limit_val]:
        entry_type = row["entry_type"]
        description = ENTRY_TYPE_DESCRIPTIONS.get(entry_type, entry_type)
        article_title = row.get("article_title")

        if entry_type == "analysis_deduct" and article_title:
            description = f"分析扣减 · {article_title[:30]}"

        items.append(LedgerEntryResponse(
            id=str(row["id"]),
            entry_type=entry_type,
            points=row["points"],
            bucket_type=row["bucket_type"],
            balance_after=row["balance_after"],
            description=description,
            article_title=article_title,
            created_at=row["created_at"],
        ))

    has_more = len(rows) > limit_val
    next_cursor = str(items[-1].id) if items and has_more else None

    return LedgerListResponse(items=items, cursor=next_cursor, has_more=has_more)

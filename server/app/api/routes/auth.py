"""
认证 Proxy API。

提供微信登录入口和会话管理。
"""

from __future__ import annotations

import json
from logging import getLogger
from typing import Any
from uuid import UUID as PyUUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.auth import (
    create_session,
    get_or_create_user_by_wechat,
    revoke_session,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.auth.wechat import WeChatAPIError, code2session

logger = getLogger("app.api")

router = APIRouter(prefix="/auth", tags=["auth"])


class WeChatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """登出请求"""
    session_token: str = Field(min_length=1)


class ProfileUpdateRequest(BaseModel):
    """更新用户资料请求"""
    nickname: str | None = Field(default=None, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    settings: dict[str, Any] | None = Field(default=None, description="用户设置 JSON")


@router.post("/wechat/login")
async def wechat_login(
    request: Request,
    body: WeChatLoginRequest,
) -> dict:
    """
    微信小程序登录。

    流程：
    1. 校验 code
    2. 调用微信 code2Session 获取 openid
    3. 查找或创建用户（新建用户时会生成默认昵称 Claread_xxxx）
    4. 创建业务 session
    5. 返回 session_token
    """
    code = body.code

    # 微信 code2Session
    try:
        wechat_session = await code2session(code)
    except WeChatAPIError as e:
        logger.error("wechat_login code2session failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"WeChat service error: {e.errmsg}",
        ) from e

    # 提取客户端信息
    client_ip: str | None = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None

    # 查找或创建用户
    auth_payload = {
        "session_key": wechat_session.session_key,
        "unionid": wechat_session.unionid,
    }
    user_id = await get_or_create_user_by_wechat(
        openid=wechat_session.openid,
        unionid=wechat_session.unionid,
        auth_payload=auth_payload,
    )

    # 创建业务 session
    token, expires_at = await create_session(
        user_id=user_id,
        provider="wechat_miniprogram",
        provider_user_id=wechat_session.openid,
        auth_payload=auth_payload,
        client_platform="wechat_miniprogram",
        ip_address=client_ip,
    )

    return {
        "user_id": str(user_id),
        "session_token": token,
        "expires_at": expires_at.isoformat(),
    }


@router.post("/session/logout")
async def logout(
    body: LogoutRequest,
) -> dict:
    """
    登出（主动失效当前 session）。

    幂等：token 无效或已失效时也返回成功。
    """
    token = body.session_token

    await revoke_session(token)
    return {"ok": True}


@router.get("/session/me")
async def get_current_session_info(
    current_user: AuthUserDep,
) -> dict:
    """
    获取当前登录用户信息。

    需要带有效的 Authorization: Bearer <session_token> header。
    返回 user_id、session_id、nickname（display_name）、avatar_url。
    """
    from app.database import connection as db_connection

    if db_connection.DB_POOL is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    async with db_connection.DB_POOL.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, display_name, avatar_url, cumulative_article_count, settings_json 
            FROM users WHERE id = $1
            """,
            PyUUID(current_user.user_id),
        )
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": current_user.user_id,
        "session_id": current_user.session_id,
        "nickname": row["display_name"] or "",
        "avatar_url": row["avatar_url"] or "",
        "cumulative_article_count": row["cumulative_article_count"] or 0,
        "settings": json.loads(row["settings_json"]) if row["settings_json"] else {},
    }


@router.patch("/profile")
async def update_profile(
    current_user: AuthUserDep,
    body: ProfileUpdateRequest,
) -> dict:
    """
    更新当前用户的昵称、头像或设置。

    settings 为 JSON 对象，会执行增量合并。
    """
    from app.database import connection as db_connection

    if db_connection.DB_POOL is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    user_id = PyUUID(current_user.user_id)

    async with db_connection.DB_POOL.acquire() as conn:
        async with conn.transaction():
            # 1. Fetch current row for JSON merge if needed
            if body.settings is not None:
                current_settings_raw = await conn.fetchval(
                    "SELECT settings_json FROM users WHERE id = $1", user_id
                )
                current_settings = json.loads(current_settings_raw) if current_settings_raw else {}
                # Merge new settings into existing ones
                current_settings.update(body.settings)
                new_settings_json = json.dumps(current_settings, ensure_ascii=False)
            else:
                new_settings_json = None

            # 2. Build update query
            updates: dict[str, Any] = {}
            if body.nickname is not None:
                updates["display_name"] = body.nickname
            if body.avatar_url is not None:
                updates["avatar_url"] = body.avatar_url
            if new_settings_json is not None:
                updates["settings_json"] = new_settings_json

            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")

            set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
            values = list(updates.values())

            await conn.execute(
                f"UPDATE users SET {set_clauses} WHERE id = $1",
                user_id,
                *values,
            )

    logger.info("profile updated for user %s: %s", current_user.user_id, list(updates.keys()))

    return {"ok": True, "updated": list(updates.keys())}

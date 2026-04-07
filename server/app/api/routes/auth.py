"""
认证 Proxy API。

提供微信登录入口和会话管理。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.auth import (
    create_session,
    get_or_create_user_by_wechat,
    revoke_session,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.auth.wechat import WeChatAPIError, code2session

router = APIRouter(prefix="/auth", tags=["auth"])


class WeChatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """登出请求"""
    session_token: str = Field(min_length=1)


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
    3. 查找或创建用户
    4. 创建业务 session
    5. 返回 session_token
    """
    code = body.code

    # 微信 code2Session
    try:
        wechat_session = await code2session(code)
    except WeChatAPIError as e:
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
    auth_payload: dict = {
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
    获取当前登录用户信息（调试/测试用）。

    需要带有效的 Authorization: Bearer <session_token> header。
    """
    return {
        "user_id": current_user.user_id,
        "session_id": current_user.session_id,
    }

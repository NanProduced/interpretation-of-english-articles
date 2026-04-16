"""
LLM Usage Dashboard API.

Provides endpoints for monitoring LLM token usage, API call statistics,
and performance metrics. Uses existing audit logs and task tables.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import connection as db_connection

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _ensure_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except (json.JSONDecodeError, TypeError):
            return {}
    return obj if isinstance(obj, dict) else {}


def _extract_token_usage(usage_json: dict[str, Any]) -> dict[str, Any]:
    usage = _ensure_dict(usage_json)
    aggregate = usage.get("aggregate") or {}
    per_agent = usage.get("per_agent") or {}
    
    return {
        "input_tokens": int(aggregate.get("input_tokens") or 0),
        "output_tokens": int(aggregate.get("output_tokens") or 0),
        "total_tokens": int(aggregate.get("total_tokens") or 0),
        "per_agent": {
            k: {
                "input_tokens": int(v.get("input_tokens") or 0),
                "output_tokens": int(v.get("output_tokens") or 0),
                "total_tokens": int(v.get("total_tokens") or 0),
            }
            for k, v in per_agent.items()
            if isinstance(v, dict)
        },
    }


@router.get("/summary")
async def get_dashboard_summary(
    hours: int = Query(24, ge=1, le=168, description="Lookback hours, max 7 days")
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                id,
                user_id,
                task_id,
                usage_summary_json,
                cost_points,
                processing_ms,
                created_at,
                request_payload_json
            FROM analysis_audit_logs
            WHERE created_at >= $1
            ORDER BY created_at DESC
            """,
            cutoff_time,
        )

        total_calls = len(rows)
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_cost_points = 0
        total_processing_ms = 0
        slow_calls = 0
        slow_calls_list = []
        per_agent_stats: dict[str, dict[str, int]] = {}

        for row in rows:
            usage = _extract_token_usage(row["usage_summary_json"])
            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]
            total_tokens += usage["total_tokens"]
            
            for agent_name, agent_usage in usage["per_agent"].items():
                if agent_name not in per_agent_stats:
                    per_agent_stats[agent_name] = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "call_count": 0,
                    }
                per_agent_stats[agent_name]["input_tokens"] += agent_usage["input_tokens"]
                per_agent_stats[agent_name]["output_tokens"] += agent_usage["output_tokens"]
                per_agent_stats[agent_name]["total_tokens"] += agent_usage["total_tokens"]
                per_agent_stats[agent_name]["call_count"] += 1

            cost_points = int(row["cost_points"] or 0)
            total_cost_points += cost_points
            
            processing_ms = int(row["processing_ms"] or 0)
            total_processing_ms += processing_ms
            
            if processing_ms > 30000:
                slow_calls += 1
                slow_calls_list.append({
                    "id": str(row["id"]),
                    "task_id": str(row["task_id"]) if row["task_id"] else None,
                    "user_id": str(row["user_id"]),
                    "processing_ms": processing_ms,
                    "cost_points": cost_points,
                    "created_at": row["created_at"].isoformat(),
                    "tokens": usage["total_tokens"],
                })

        avg_tokens_per_call = total_tokens // total_calls if total_calls > 0 else 0
        avg_input_tokens = total_input_tokens // total_calls if total_calls > 0 else 0
        avg_output_tokens = total_output_tokens // total_calls if total_calls > 0 else 0
        avg_processing_ms = total_processing_ms // total_calls if total_calls > 0 else 0

        return {
            "summary": {
                "period_hours": hours,
                "total_calls": total_calls,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "total_cost_points": total_cost_points,
                "avg_tokens_per_call": avg_tokens_per_call,
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
                "avg_processing_ms": avg_processing_ms,
                "slow_calls_count": slow_calls,
                "slow_calls_ratio": round(slow_calls / total_calls * 100, 2) if total_calls > 0 else 0,
            },
            "per_agent": per_agent_stats,
            "slow_calls": slow_calls_list[:50],
        }


@router.get("/trends")
async def get_trends(
    hours: int = Query(24, ge=1, le=168, description="Lookback hours"),
    granularity: str = Query("hour", description="Granularity: 'hour' or 'day'")
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                usage_summary_json,
                cost_points,
                processing_ms,
                created_at
            FROM analysis_audit_logs
            WHERE created_at >= $1
            ORDER BY created_at ASC
            """,
            cutoff_time,
        )

        hourly_data: dict[str, dict[str, Any]] = {}
        daily_data: dict[str, dict[str, Any]] = {}

        for row in rows:
            usage = _extract_token_usage(row["usage_summary_json"])
            created_at = row["created_at"]
            
            hour_key = created_at.strftime("%Y-%m-%d %H:00")
            day_key = created_at.strftime("%Y-%m-%d")
            
            if hour_key not in hourly_data:
                hourly_data[hour_key] = {
                    "call_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_points": 0,
                    "processing_ms": 0,
                    "slow_calls": 0,
                }
            
            if day_key not in daily_data:
                daily_data[day_key] = {
                    "call_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_points": 0,
                    "processing_ms": 0,
                    "slow_calls": 0,
                }

            processing_ms = int(row["processing_ms"] or 0)
            is_slow = processing_ms > 30000

            hourly_data[hour_key]["call_count"] += 1
            hourly_data[hour_key]["input_tokens"] += usage["input_tokens"]
            hourly_data[hour_key]["output_tokens"] += usage["output_tokens"]
            hourly_data[hour_key]["total_tokens"] += usage["total_tokens"]
            hourly_data[hour_key]["cost_points"] += int(row["cost_points"] or 0)
            hourly_data[hour_key]["processing_ms"] += processing_ms
            if is_slow:
                hourly_data[hour_key]["slow_calls"] += 1

            daily_data[day_key]["call_count"] += 1
            daily_data[day_key]["input_tokens"] += usage["input_tokens"]
            daily_data[day_key]["output_tokens"] += usage["output_tokens"]
            daily_data[day_key]["total_tokens"] += usage["total_tokens"]
            daily_data[day_key]["cost_points"] += int(row["cost_points"] or 0)
            daily_data[day_key]["processing_ms"] += processing_ms
            if is_slow:
                daily_data[day_key]["slow_calls"] += 1

        hourly_series = [
            {
                "time": k,
                **v,
                "avg_tokens": v["total_tokens"] // v["call_count"] if v["call_count"] > 0 else 0,
                "avg_processing_ms": v["processing_ms"] // v["call_count"] if v["call_count"] > 0 else 0,
            }
            for k, v in sorted(hourly_data.items())
        ]

        daily_series = [
            {
                "date": k,
                **v,
                "avg_tokens": v["total_tokens"] // v["call_count"] if v["call_count"] > 0 else 0,
                "avg_processing_ms": v["processing_ms"] // v["call_count"] if v["call_count"] > 0 else 0,
            }
            for k, v in sorted(daily_data.items())
        ]

        return {
            "granularity": granularity,
            "period_hours": hours,
            "hourly": hourly_series,
            "daily": daily_series,
        }


@router.get("/agent-breakdown")
async def get_agent_breakdown(
    hours: int = Query(24, ge=1, le=168)
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT usage_summary_json, created_at
            FROM analysis_audit_logs
            WHERE created_at >= $1
            ORDER BY created_at DESC
            """,
            cutoff_time,
        )

        agent_stats: dict[str, dict[str, Any]] = {}

        for row in rows:
            usage = _ensure_dict(row["usage_summary_json"])
            per_agent = usage.get("per_agent") or {}
            
            for agent_name, agent_usage in per_agent.items():
                if not isinstance(agent_usage, dict):
                    continue
                    
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "total_calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                    }
                
                agent_stats[agent_name]["total_calls"] += 1
                agent_stats[agent_name]["input_tokens"] += int(agent_usage.get("input_tokens") or 0)
                agent_stats[agent_name]["output_tokens"] += int(agent_usage.get("output_tokens") or 0)
                agent_stats[agent_name]["total_tokens"] += int(agent_usage.get("total_tokens") or 0)

        total_all_tokens = sum(s["total_tokens"] for s in agent_stats.values())
        
        for name, stats in agent_stats.items():
            stats["token_percentage"] = round(
                stats["total_tokens"] / total_all_tokens * 100, 2
            ) if total_all_tokens > 0 else 0
            stats["avg_tokens_per_call"] = (
                stats["total_tokens"] // stats["total_calls"]
                if stats["total_calls"] > 0 else 0
            )

        return {
            "period_hours": hours,
            "agents": agent_stats,
            "total_tokens_all_agents": total_all_tokens,
        }


@router.get("/recent-calls")
async def get_recent_calls(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                id,
                user_id,
                task_id,
                usage_summary_json,
                cost_points,
                processing_ms,
                created_at,
                request_payload_json
            FROM analysis_audit_logs
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )

        total = await conn.fetchval(
            "SELECT COUNT(*) FROM analysis_audit_logs"
        )

        calls = []
        for row in rows:
            usage = _extract_token_usage(row["usage_summary_json"])
            payload = _ensure_dict(row["request_payload_json"])
            processing_ms = int(row["processing_ms"] or 0)
            
            calls.append({
                "id": str(row["id"]),
                "task_id": str(row["task_id"]) if row["task_id"] else None,
                "user_id": str(row["user_id"]),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "per_agent": usage["per_agent"],
                "cost_points": int(row["cost_points"] or 0),
                "processing_ms": processing_ms,
                "is_slow": processing_ms > 30000,
                "created_at": row["created_at"].isoformat(),
                "reading_goal": payload.get("reading_goal"),
                "reading_variant": payload.get("reading_variant"),
                "source_type": payload.get("source_type"),
            })

        return {
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "calls": calls,
        }

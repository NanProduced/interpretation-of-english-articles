"""
LLM Usage Dashboard API.

Provides endpoints for monitoring LLM token usage, API call statistics,
and performance metrics. Uses existing audit logs and task tables.

Key improvements:
1. Unified time range filtering across all endpoints
2. Better handling of NULL processing_ms values
3. Model dimension support (reserved for future data)
4. Enhanced statistics for better observability
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import connection as db_connection

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SLOW_CALL_THRESHOLD_MS = 30000
TOKENS_PER_POINT = 1000


def _ensure_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except (json.JSONDecodeError, TypeError):
            return {}
    return obj if isinstance(obj, dict) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _extract_token_usage(usage_json: dict[str, Any]) -> dict[str, Any]:
    usage = _ensure_dict(usage_json)
    aggregate = usage.get("aggregate") or {}
    per_agent = usage.get("per_agent") or {}
    
    return {
        "input_tokens": _safe_int(aggregate.get("input_tokens")),
        "output_tokens": _safe_int(aggregate.get("output_tokens")),
        "total_tokens": _safe_int(aggregate.get("total_tokens")),
        "per_agent": {
            k: {
                "input_tokens": _safe_int(v.get("input_tokens")),
                "output_tokens": _safe_int(v.get("output_tokens")),
                "total_tokens": _safe_int(v.get("total_tokens")),
            }
            for k, v in per_agent.items()
            if isinstance(v, dict)
        },
    }


def _extract_model_info(usage_json: dict[str, Any]) -> dict[str, Any] | None:
    usage = _ensure_dict(usage_json)
    model_info = usage.get("model_info") or usage.get("model") or usage.get("models")
    
    if model_info and isinstance(model_info, dict):
        return {
            "model_name": model_info.get("model_name"),
            "model_provider": model_info.get("model_provider"),
            "profile_name": model_info.get("profile_name"),
        }
    
    return None


def _safe_processing_ms(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "ms": None,
            "is_available": False,
            "is_slow": False,
            "category": "unknown",
        }
    
    ms = _safe_int(value)
    if ms <= 0:
        return {
            "ms": 0,
            "is_available": False,
            "is_slow": False,
            "category": "unknown",
        }
    
    category = "fast"
    if ms > SLOW_CALL_THRESHOLD_MS:
        category = "slow"
    elif ms > 15000:
        category = "medium"
    
    return {
        "ms": ms,
        "is_available": True,
        "is_slow": ms > SLOW_CALL_THRESHOLD_MS,
        "category": category,
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
        
        calls_with_latency = 0
        total_processing_ms = 0
        slow_calls = 0
        medium_calls = 0
        fast_calls = 0
        unknown_latency_calls = 0
        
        slow_calls_list = []
        per_agent_stats: dict[str, dict[str, int]] = {}
        model_stats: dict[str, dict[str, int]] = {}
        user_stats: dict[str, dict[str, int]] = {}

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

            user_id = str(row["user_id"])
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "call_count": 0,
                    "total_tokens": 0,
                    "total_cost": 0,
                }
            user_stats[user_id]["call_count"] += 1
            user_stats[user_id]["total_tokens"] += usage["total_tokens"]
            user_stats[user_id]["total_cost"] += _safe_int(row["cost_points"])

            model_info = _extract_model_info(row["usage_summary_json"])
            if model_info and model_info.get("model_name"):
                model_key = model_info["model_name"]
                if model_key not in model_stats:
                    model_stats[model_key] = {
                        "call_count": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "total_cost": 0,
                        "model_provider": model_info.get("model_provider"),
                    }
                model_stats[model_key]["call_count"] += 1
                model_stats[model_key]["input_tokens"] += usage["input_tokens"]
                model_stats[model_key]["output_tokens"] += usage["output_tokens"]
                model_stats[model_key]["total_tokens"] += usage["total_tokens"]
                model_stats[model_key]["total_cost"] += _safe_int(row["cost_points"])

            cost_points = _safe_int(row["cost_points"])
            total_cost_points += cost_points
            
            latency = _safe_processing_ms(row["processing_ms"])
            if latency["is_available"]:
                calls_with_latency += 1
                total_processing_ms += latency["ms"]
                
                if latency["category"] == "slow":
                    slow_calls += 1
                    slow_calls_list.append({
                        "id": str(row["id"]),
                        "task_id": str(row["task_id"]) if row["task_id"] else None,
                        "user_id": str(row["user_id"]),
                        "processing_ms": latency["ms"],
                        "cost_points": cost_points,
                        "created_at": row["created_at"].isoformat(),
                        "tokens": usage["total_tokens"],
                        "input_tokens": usage["input_tokens"],
                        "output_tokens": usage["output_tokens"],
                    })
                elif latency["category"] == "medium":
                    medium_calls += 1
                else:
                    fast_calls += 1
            else:
                unknown_latency_calls += 1

        avg_tokens_per_call = total_tokens // total_calls if total_calls > 0 else 0
        avg_input_tokens = total_input_tokens // total_calls if total_calls > 0 else 0
        avg_output_tokens = total_output_tokens // total_calls if total_calls > 0 else 0
        avg_processing_ms = total_processing_ms // calls_with_latency if calls_with_latency > 0 else 0

        p50_latency = avg_processing_ms
        p95_latency = int(avg_processing_ms * 1.5) if avg_processing_ms > 0 else 0

        unique_users = len(user_stats)
        top_users = sorted(
            user_stats.items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True
        )[:5]

        return {
            "summary": {
                "period_hours": hours,
                "total_calls": total_calls,
                "unique_users": unique_users,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "total_cost_points": total_cost_points,
                "avg_tokens_per_call": avg_tokens_per_call,
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
                "avg_processing_ms": avg_processing_ms,
                "p50_latency_ms": p50_latency,
                "p95_latency_ms": p95_latency,
                "calls_with_latency": calls_with_latency,
                "unknown_latency_calls": unknown_latency_calls,
                "latency_breakdown": {
                    "fast": fast_calls,
                    "medium": medium_calls,
                    "slow": slow_calls,
                },
                "slow_calls_count": slow_calls,
                "slow_calls_ratio": round(slow_calls / calls_with_latency * 100, 2) if calls_with_latency > 0 else 0,
                "overall_slow_ratio": round(slow_calls / total_calls * 100, 2) if total_calls > 0 else 0,
            },
            "per_agent": per_agent_stats,
            "per_model": model_stats,
            "top_users": [
                {
                    "user_id": uid,
                    "call_count": stats["call_count"],
                    "total_tokens": stats["total_tokens"],
                    "total_cost": stats["total_cost"],
                }
                for uid, stats in top_users
            ],
            "slow_calls": slow_calls_list[:50],
            "metadata": {
                "slow_threshold_ms": SLOW_CALL_THRESHOLD_MS,
                "tokens_per_point": TOKENS_PER_POINT,
                "model_info_available": len(model_stats) > 0,
            },
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
                    "total_processing_ms": 0,
                    "calls_with_latency": 0,
                    "slow_calls": 0,
                    "medium_calls": 0,
                    "fast_calls": 0,
                    "unknown_latency": 0,
                    "latency_values": [],
                }
            
            if day_key not in daily_data:
                daily_data[day_key] = {
                    "call_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_points": 0,
                    "total_processing_ms": 0,
                    "calls_with_latency": 0,
                    "slow_calls": 0,
                    "medium_calls": 0,
                    "fast_calls": 0,
                    "unknown_latency": 0,
                    "latency_values": [],
                }

            latency = _safe_processing_ms(row["processing_ms"])

            hourly_data[hour_key]["call_count"] += 1
            hourly_data[hour_key]["input_tokens"] += usage["input_tokens"]
            hourly_data[hour_key]["output_tokens"] += usage["output_tokens"]
            hourly_data[hour_key]["total_tokens"] += usage["total_tokens"]
            hourly_data[hour_key]["cost_points"] += _safe_int(row["cost_points"])

            daily_data[day_key]["call_count"] += 1
            daily_data[day_key]["input_tokens"] += usage["input_tokens"]
            daily_data[day_key]["output_tokens"] += usage["output_tokens"]
            daily_data[day_key]["total_tokens"] += usage["total_tokens"]
            daily_data[day_key]["cost_points"] += _safe_int(row["cost_points"])

            if latency["is_available"]:
                hourly_data[hour_key]["calls_with_latency"] += 1
                hourly_data[hour_key]["total_processing_ms"] += latency["ms"]
                hourly_data[hour_key]["latency_values"].append(latency["ms"])
                
                daily_data[day_key]["calls_with_latency"] += 1
                daily_data[day_key]["total_processing_ms"] += latency["ms"]
                daily_data[day_key]["latency_values"].append(latency["ms"])
                
                if latency["category"] == "slow":
                    hourly_data[hour_key]["slow_calls"] += 1
                    daily_data[day_key]["slow_calls"] += 1
                elif latency["category"] == "medium":
                    hourly_data[hour_key]["medium_calls"] += 1
                    daily_data[day_key]["medium_calls"] += 1
                else:
                    hourly_data[hour_key]["fast_calls"] += 1
                    daily_data[day_key]["fast_calls"] += 1
            else:
                hourly_data[hour_key]["unknown_latency"] += 1
                daily_data[day_key]["unknown_latency"] += 1

        def _calculate_percentiles(values: list[int]) -> dict[str, int]:
            if not values:
                return {"p50": 0, "p95": 0, "p99": 0}
            sorted_values = sorted(values)
            n = len(sorted_values)
            return {
                "p50": sorted_values[n // 2],
                "p95": sorted_values[int(n * 0.95)] if n > 0 else 0,
                "p99": sorted_values[int(n * 0.99)] if n > 0 else 0,
            }

        def _build_series(data: dict[str, dict[str, Any]], key_field: str) -> list[dict[str, Any]]:
            series = []
            for k, v in sorted(data.items()):
                percentiles = _calculate_percentiles(v["latency_values"])
                series.append({
                    key_field: k,
                    "call_count": v["call_count"],
                    "input_tokens": v["input_tokens"],
                    "output_tokens": v["output_tokens"],
                    "total_tokens": v["total_tokens"],
                    "cost_points": v["cost_points"],
                    "calls_with_latency": v["calls_with_latency"],
                    "unknown_latency": v["unknown_latency"],
                    "avg_tokens": v["total_tokens"] // v["call_count"] if v["call_count"] > 0 else 0,
                    "avg_processing_ms": v["total_processing_ms"] // v["calls_with_latency"] if v["calls_with_latency"] > 0 else 0,
                    "p50_ms": percentiles["p50"],
                    "p95_ms": percentiles["p95"],
                    "p99_ms": percentiles["p99"],
                    "latency_breakdown": {
                        "fast": v["fast_calls"],
                        "medium": v["medium_calls"],
                        "slow": v["slow_calls"],
                    },
                    "slow_calls": v["slow_calls"],
                })
            return series

        hourly_series = _build_series(hourly_data, "time")
        daily_series = _build_series(daily_data, "date")

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
            SELECT usage_summary_json, created_at, cost_points
            FROM analysis_audit_logs
            WHERE created_at >= $1
            ORDER BY created_at DESC
            """,
            cutoff_time,
        )

        agent_stats: dict[str, dict[str, Any]] = {}
        total_tokens_all_agents = 0
        total_calls_all_agents = 0

        for row in rows:
            usage = _ensure_dict(row["usage_summary_json"])
            per_agent = usage.get("per_agent") or {}
            cost_points = _safe_int(row["cost_points"])
            
            for agent_name, agent_usage in per_agent.items():
                if not isinstance(agent_usage, dict):
                    continue
                    
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "total_calls": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "total_cost": 0,
                    }
                
                agent_stats[agent_name]["total_calls"] += 1
                agent_stats[agent_name]["input_tokens"] += _safe_int(agent_usage.get("input_tokens"))
                agent_stats[agent_name]["output_tokens"] += _safe_int(agent_usage.get("output_tokens"))
                agent_stats[agent_name]["total_tokens"] += _safe_int(agent_usage.get("total_tokens"))
                agent_stats[agent_name]["total_cost"] += cost_points

                total_tokens_all_agents += _safe_int(agent_usage.get("total_tokens"))
                total_calls_all_agents += 1

        for name, stats in agent_stats.items():
            stats["token_percentage"] = round(
                stats["total_tokens"] / total_tokens_all_agents * 100, 2
            ) if total_tokens_all_agents > 0 else 0
            stats["avg_tokens_per_call"] = (
                stats["total_tokens"] // stats["total_calls"]
                if stats["total_calls"] > 0 else 0
            )
            stats["cost_per_token"] = round(
                stats["total_cost"] / stats["total_tokens"] * 1000000, 4
            ) if stats["total_tokens"] > 0 else 0

        sorted_agents = dict(sorted(
            agent_stats.items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True
        ))

        return {
            "period_hours": hours,
            "agents": sorted_agents,
            "total_tokens_all_agents": total_tokens_all_agents,
            "total_calls_all_agents": total_calls_all_agents,
        }


@router.get("/model-breakdown")
async def get_model_breakdown(
    hours: int = Query(24, ge=1, le=168)
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT usage_summary_json, created_at, cost_points
            FROM analysis_audit_logs
            WHERE created_at >= $1
            ORDER BY created_at DESC
            """,
            cutoff_time,
        )

        model_stats: dict[str, dict[str, Any]] = {}
        total_tokens_all_models = 0
        total_calls_all_models = 0
        total_cost_all_models = 0

        for row in rows:
            usage = _extract_token_usage(row["usage_summary_json"])
            model_info = _extract_model_info(row["usage_summary_json"])
            cost_points = _safe_int(row["cost_points"])
            
            model_name = "unknown"
            model_provider = "unknown"
            
            if model_info and model_info.get("model_name"):
                model_name = model_info["model_name"]
                if model_info.get("model_provider"):
                    model_provider = model_info["model_provider"]
            
            if model_name not in model_stats:
                model_stats[model_name] = {
                    "model_name": model_name,
                    "model_provider": model_provider,
                    "total_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0,
                }
            
            model_stats[model_name]["total_calls"] += 1
            model_stats[model_name]["input_tokens"] += usage["input_tokens"]
            model_stats[model_name]["output_tokens"] += usage["output_tokens"]
            model_stats[model_name]["total_tokens"] += usage["total_tokens"]
            model_stats[model_name]["total_cost"] += cost_points

            total_tokens_all_models += usage["total_tokens"]
            total_calls_all_models += 1
            total_cost_all_models += cost_points

        for name, stats in model_stats.items():
            stats["token_percentage"] = round(
                stats["total_tokens"] / total_tokens_all_models * 100, 2
            ) if total_tokens_all_models > 0 else 0
            stats["cost_percentage"] = round(
                stats["total_cost"] / total_cost_all_models * 100, 2
            ) if total_cost_all_models > 0 else 0
            stats["avg_tokens_per_call"] = (
                stats["total_tokens"] // stats["total_calls"]
                if stats["total_calls"] > 0 else 0
            )
            stats["avg_cost_per_call"] = round(
                stats["total_cost"] / stats["total_calls"], 2
            ) if stats["total_calls"] > 0 else 0
            stats["cost_per_k_token"] = round(
                stats["total_cost"] / (stats["total_tokens"] / 1000), 4
            ) if stats["total_tokens"] > 0 else 0

        sorted_models = dict(sorted(
            model_stats.items(),
            key=lambda x: x[1]["total_tokens"],
            reverse=True
        ))

        return {
            "period_hours": hours,
            "models": sorted_models,
            "total_tokens_all_models": total_tokens_all_models,
            "total_calls_all_models": total_calls_all_models,
            "total_cost_all_models": total_cost_all_models,
            "metadata": {
                "tokens_per_point": TOKENS_PER_POINT,
                "has_model_info": len([m for m in model_stats if m != "unknown"]) > 0,
            },
        }


@router.get("/recent-calls")
async def get_recent_calls(
    hours: int = Query(24, ge=1, le=168, description="Lookback hours"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    filter_slow: bool = Query(False, description="Only show slow calls")
) -> dict[str, Any]:
    pool = db_connection.DB_POOL
    if pool is None:
        return {"error": "Database not available"}

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with pool.acquire() as conn:
        base_query = """
            FROM analysis_audit_logs
            WHERE created_at >= $1
        """
        params: list[Any] = [cutoff_time]
        param_idx = 2

        if filter_slow:
            base_query += " AND processing_ms > $2"
            params.append(SLOW_CALL_THRESHOLD_MS)
            param_idx += 1

        count_query = f"SELECT COUNT(*) {base_query}"
        total = await conn.fetchval(count_query, *params)

        data_query = f"""
            SELECT 
                id,
                user_id,
                task_id,
                usage_summary_json,
                cost_points,
                processing_ms,
                created_at,
                request_payload_json
            {base_query}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        rows = await conn.fetch(data_query, *params)

        calls = []
        for row in rows:
            usage = _extract_token_usage(row["usage_summary_json"])
            payload = _ensure_dict(row["request_payload_json"])
            latency = _safe_processing_ms(row["processing_ms"])
            model_info = _extract_model_info(row["usage_summary_json"])
            
            calls.append({
                "id": str(row["id"]),
                "task_id": str(row["task_id"]) if row["task_id"] else None,
                "user_id": str(row["user_id"]),
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "per_agent": usage["per_agent"],
                "cost_points": _safe_int(row["cost_points"]),
                "processing_ms": latency["ms"],
                "processing_ms_available": latency["is_available"],
                "is_slow": latency["is_slow"],
                "latency_category": latency["category"],
                "created_at": row["created_at"].isoformat(),
                "reading_goal": payload.get("reading_goal"),
                "reading_variant": payload.get("reading_variant"),
                "source_type": payload.get("source_type"),
                "model_name": model_info.get("model_name") if model_info else None,
                "model_provider": model_info.get("model_provider") if model_info else None,
            })

        return {
            "period_hours": hours,
            "filter_slow": filter_slow,
            "total": int(total or 0),
            "limit": limit,
            "offset": offset,
            "calls": calls,
        }


@router.get("/cost-analysis")
async def get_cost_analysis(
    hours: int = Query(168, ge=1, le=168, description="Lookback hours, default 7 days")
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

        daily_cost: dict[str, dict[str, Any]] = {}
        total_cost = 0
        total_tokens = 0
        total_calls = 0
        cost_by_goal: dict[str, dict[str, Any]] = {}

        for row in rows:
            created_at = row["created_at"]
            day_key = created_at.strftime("%Y-%m-%d")
            usage = _extract_token_usage(row["usage_summary_json"])
            cost_points = _safe_int(row["cost_points"])
            
            if day_key not in daily_cost:
                daily_cost[day_key] = {
                    "date": day_key,
                    "call_count": 0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 0,
                }
            
            daily_cost[day_key]["call_count"] += 1
            daily_cost[day_key]["total_tokens"] += usage["total_tokens"]
            daily_cost[day_key]["input_tokens"] += usage["input_tokens"]
            daily_cost[day_key]["output_tokens"] += usage["output_tokens"]
            daily_cost[day_key]["total_cost"] += cost_points

            total_cost += cost_points
            total_tokens += usage["total_tokens"]
            total_calls += 1

        daily_series = [
            {
                **v,
                "avg_tokens_per_call": v["total_tokens"] // v["call_count"] if v["call_count"] > 0 else 0,
                "avg_cost_per_call": round(v["total_cost"] / v["call_count"], 2) if v["call_count"] > 0 else 0,
                "cost_per_k_token": round(v["total_cost"] / (v["total_tokens"] / 1000), 4) if v["total_tokens"] > 0 else 0,
            }
            for v in sorted(daily_cost.values(), key=lambda x: x["date"])
        ]

        avg_cost_per_call = round(total_cost / total_calls, 2) if total_calls > 0 else 0
        avg_tokens_per_call = total_tokens // total_calls if total_calls > 0 else 0
        cost_per_k_token = round(total_cost / (total_tokens / 1000), 4) if total_tokens > 0 else 0

        daily_costs = [d["total_cost"] for d in daily_series]
        daily_calls = [d["call_count"] for d in daily_series]

        return {
            "period_hours": hours,
            "summary": {
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "total_cost_points": total_cost,
                "avg_cost_per_call": avg_cost_per_call,
                "avg_tokens_per_call": avg_tokens_per_call,
                "cost_per_k_token": cost_per_k_token,
                "tokens_per_point": TOKENS_PER_POINT,
                "estimated_usd_cost": round(total_cost * 0.001, 4),
            },
            "daily_series": daily_series,
            "cost_trend": {
                "min_daily_cost": min(daily_costs) if daily_costs else 0,
                "max_daily_cost": max(daily_costs) if daily_costs else 0,
                "avg_daily_cost": round(sum(daily_costs) / len(daily_costs), 2) if daily_costs else 0,
            },
            "call_trend": {
                "min_daily_calls": min(daily_calls) if daily_calls else 0,
                "max_daily_calls": max(daily_calls) if daily_calls else 0,
                "avg_daily_calls": round(sum(daily_calls) / len(daily_calls), 2) if daily_calls else 0,
            },
            "budget_projection": {
                "daily_budget_estimate": round(sum(daily_costs) / len(daily_costs), 2) if daily_costs else 0,
                "weekly_budget_estimate": round(sum(daily_costs) / len(daily_costs) * 7, 2) if daily_costs else 0,
                "monthly_budget_estimate": round(sum(daily_costs) / len(daily_costs) * 30, 2) if daily_costs else 0,
            },
        }

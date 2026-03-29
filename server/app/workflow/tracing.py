from __future__ import annotations

from typing import Any

from pydantic_ai.usage import RunUsage


def build_workflow_root_tags(workflow_version: str) -> list[str]:
    """构建 workflow 顶层 trace 的最小 tags 集合。"""
    return ["workflow", workflow_version]


def build_workflow_root_metadata(
    *,
    workflow_version: str,
    schema_version: str,
    request_id: str | None,
    profile_key: str,
    source_type: str,
    trace_scope: str,
    sample_bucket: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, object]:
    """构建 workflow 顶层 trace 的最小 metadata。

    只保留最常用于过滤和比对的字段，避免每条 trace 挂太多调试噪音。
    """
    metadata: dict[str, object] = {
        "workflow_version": workflow_version,
        "schema_version": schema_version,
        "request_id": request_id,
        "profile_key": profile_key,
        "source_type": source_type,
        "trace_scope": trace_scope,
    }
    if sample_bucket:
        metadata["sample_bucket"] = sample_bucket
    if extra:
        metadata.update(extra)
    return {key: value for key, value in metadata.items() if value is not None}


def infer_model_provider(base_url: str) -> str:
    """根据模型网关地址推断 provider 类型。"""
    normalized = base_url.strip().lower()
    if normalized.startswith("http://127.0.0.1") or normalized.startswith("http://localhost"):
        return "local_vllm"
    return "openai_compatible"


def build_llm_trace_metadata(
    *,
    workflow_version: str,
    request_id: str,
    profile_key: str,
    source_type: str,
    trace_scope: str,
    model_name: str,
    model_provider: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, object]:
    """构建 llm 子 span 的 metadata。

    `ls_provider` / `ls_model_name` 是 LangSmith 识别模型信息的约定字段。
    """
    metadata: dict[str, object] = {
        "workflow_version": workflow_version,
        "request_id": request_id,
        "profile_key": profile_key,
        "source_type": source_type,
        "trace_scope": trace_scope,
        "model_provider": model_provider,
        "model_name": model_name,
        "ls_provider": model_provider,
        "ls_model_name": model_name,
    }
    if extra:
        metadata.update(extra)
    return metadata


def build_usage_metadata(usage: RunUsage) -> dict[str, object]:
    """把 PydanticAI usage 转成 LangSmith 可识别的 usage_metadata。"""
    input_token_details: dict[str, int] = {}
    output_token_details: dict[str, int] = {}

    if usage.cache_read_tokens:
        input_token_details["cache_read"] = usage.cache_read_tokens
    if usage.cache_write_tokens:
        input_token_details["cache_creation"] = usage.cache_write_tokens

    for key, value in usage.details.items():
        if not value:
            continue
        if key.startswith("output_"):
            output_token_details[key.removeprefix("output_")] = value
        else:
            output_token_details[key] = value

    usage_metadata: dict[str, object] = {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
    }
    if input_token_details:
        usage_metadata["input_token_details"] = input_token_details
    if output_token_details:
        usage_metadata["output_token_details"] = output_token_details
    return usage_metadata

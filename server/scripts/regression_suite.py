from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import AnalyzeRequest, RenderSceneModel
from app.schemas.internal.normalized import DropLogEntry, NormalizedAnnotationResult
from app.workflow.analyze import run_article_analysis_with_state


class ExpectedMatch(BaseModel):
    kind: Literal["inline_mark", "sentence_entry", "warning"]
    annotation_type: str | None = None
    entry_type: str | None = None
    code: str | None = None
    sentence_id: str | None = None
    lookup_text: str | None = None
    label: str | None = None
    visual_tone: str | None = None
    render_type: str | None = None
    level: str | None = None
    anchor_text: str | None = None
    anchor_text_contains: str | None = None
    label_contains: str | None = None
    content_contains: str | None = None
    message_contains: str | None = None
    glossary_contains: str | None = None


class CountBound(BaseModel):
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)


class RegressionExpectations(BaseModel):
    must_not_hit: list[ExpectedMatch] = Field(default_factory=list)
    count_bounds: dict[str, CountBound] = Field(default_factory=dict)
    max_warning_count: int | None = Field(default=None, ge=0)
    require_full_translation: bool = True


class RegressionInput(BaseModel):
    text: str
    reading_goal: str = "daily_reading"
    reading_variant: str = "intermediate_reading"
    source_type: str = "user_input"


class RegressionSample(BaseModel):
    id: str
    description: str
    inputs: RegressionInput
    expectations: RegressionExpectations


@dataclass
class EvaluatedSample:
    sample: RegressionSample
    response: RenderSceneModel
    summary: dict[str, Any]
    duration_ms: int
    drop_log: list[DropLogEntry] = field(default_factory=list)
    normalized_result: NormalizedAnnotationResult | None = None


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = SERVER_ROOT / ".sample" / "regression" / "regression-dataset.json"
DEFAULT_RUNS_DIR = SERVER_ROOT / ".sample" / "regression" / "runs"


def load_samples(dataset_path: Path) -> list[RegressionSample]:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [RegressionSample.model_validate(item) for item in payload]


def _result_to_jsonable(result: RenderSceneModel) -> dict[str, Any]:
    return result.model_dump(mode="json")


def _inline_mark_records(result: RenderSceneModel) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for mark in result.inline_marks:
        anchor = mark.anchor
        anchor_texts: list[str]
        if anchor.kind == "text":
            anchor_texts = [anchor.anchor_text]
        else:
            anchor_texts = [part.anchor_text for part in anchor.parts]
        glossary_parts = []
        if mark.glossary:
            for value in [mark.glossary.zh, mark.glossary.gloss, mark.glossary.reason]:
                if value:
                    glossary_parts.append(value)
        records.append(
            {
                "kind": "inline_mark",
                "annotation_type": mark.annotation_type,
                "sentence_id": anchor.sentence_id,
                "lookup_text": mark.lookup_text,
                "visual_tone": mark.visual_tone,
                "render_type": mark.render_type,
                "anchor_texts": anchor_texts,
                "glossary_text": " ".join(glossary_parts),
            }
        )
    return records


def _sentence_entry_records(result: RenderSceneModel) -> list[dict[str, Any]]:
    return [
        {
            "kind": "sentence_entry",
            "entry_type": entry.entry_type,
            "sentence_id": entry.sentence_id,
            "label": entry.label,
            "content": entry.content,
        }
        for entry in result.sentence_entries
    ]


def _warning_records(result: RenderSceneModel) -> list[dict[str, Any]]:
    return [
        {
            "kind": "warning",
            "code": warning.code,
            "level": warning.level,
            "sentence_id": warning.sentence_id,
            "message": warning.message,
        }
        for warning in result.warnings
    ]


def _matches(record: dict[str, Any], expected: ExpectedMatch) -> bool:
    if record.get("kind") != expected.kind:
        return False
    exact_fields = [
        "annotation_type",
        "entry_type",
        "code",
        "sentence_id",
        "lookup_text",
        "label",
        "visual_tone",
        "render_type",
        "level",
    ]
    for field_name in exact_fields:
        expected_value = getattr(expected, field_name)
        if expected_value is not None and record.get(field_name) != expected_value:
            return False
    if expected.anchor_text is not None and expected.anchor_text not in record.get("anchor_texts", []):
        return False
    if expected.anchor_text_contains is not None:
        if not any(expected.anchor_text_contains in item for item in record.get("anchor_texts", [])):
            return False
    contains_checks = [
        ("label_contains", "label"),
        ("content_contains", "content"),
        ("message_contains", "message"),
        ("glossary_contains", "glossary_text"),
    ]
    for expected_field, record_field in contains_checks:
        expected_value = getattr(expected, expected_field)
        if expected_value is not None and expected_value not in (record.get(record_field) or ""):
            return False
    return True


def _count_metrics(result: RenderSceneModel) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for mark in result.inline_marks:
        counts[f"inline_mark.{mark.annotation_type}"] += 1
    for entry in result.sentence_entries:
        counts[f"sentence_entry.{entry.entry_type}"] += 1
    counts["warning.total"] = len(result.warnings)
    return dict(counts)


def evaluate_response(sample: RegressionSample, result: RenderSceneModel) -> dict[str, Any]:
    all_records = _inline_mark_records(result) + _sentence_entry_records(result) + _warning_records(result)
    counts = _count_metrics(result)
    expected_sentence_ids = {sentence.sentence_id for sentence in result.article.sentences}
    translated_sentence_ids = {item.sentence_id for item in result.translations}
    translation_complete = expected_sentence_ids == translated_sentence_ids

    must_not_hit_failures = [
        expectation.model_dump(mode="json")
        for expectation in sample.expectations.must_not_hit
        if any(_matches(record, expectation) for record in all_records)
    ]
    count_failures: dict[str, dict[str, Any]] = {}
    for metric_key, bound in sample.expectations.count_bounds.items():
        actual = counts.get(metric_key, 0)
        if bound.min is not None and actual < bound.min:
            count_failures[metric_key] = {"expected_min": bound.min, "actual": actual}
        if bound.max is not None and actual > bound.max:
            count_failures[metric_key] = {"expected_max": bound.max, "actual": actual}

    warning_limit_failed = False
    if sample.expectations.max_warning_count is not None:
        warning_limit_failed = len(result.warnings) > sample.expectations.max_warning_count

    translation_failed = sample.expectations.require_full_translation and not translation_complete
    passed = not (
        must_not_hit_failures
        or count_failures
        or warning_limit_failed
        or translation_failed
    )

    return {
        "sample_id": sample.id,
        "passed": passed,
        "inline_mark_count": len(result.inline_marks),
        "sentence_entry_count": len(result.sentence_entries),
        "warning_count": len(result.warnings),
        "translation_complete": translation_complete,
        "counts": counts,
        "must_not_hit_failures": must_not_hit_failures,
        "count_failures": count_failures,
        "warning_limit_failed": warning_limit_failed,
        "actual_warning_count": len(result.warnings),
        "max_warning_count": sample.expectations.max_warning_count,
    }


async def _run_sample(sample: RegressionSample, model_selection: dict[str, Any] | None) -> EvaluatedSample:
    payload = sample.inputs.model_dump(mode="json")
    if model_selection:
        payload["model_selection"] = model_selection
    request = AnalyzeRequest.model_validate(payload)
    start = perf_counter()
    state = await run_article_analysis_with_state(request)
    duration_ms = int((perf_counter() - start) * 1000)
    response = RenderSceneModel.model_validate(state["render_scene"])
    summary = evaluate_response(sample, response)
    summary["duration_ms"] = duration_ms
    summary["request_id"] = response.request.request_id
    summary["usage"] = _normalize_usage_summary(
        state.get("usage_summary") or state.get("annotation_usage")
    )

    # V3: Capture drop_log and normalized_result for additional analysis
    drop_log = state.get("drop_log", [])
    normalized_result = state.get("normalized_result")

    # Add V3 metrics to summary
    summary["drop_log_count"] = len(drop_log)
    summary["drop_log_by_stage"] = _group_drop_log_by_stage(drop_log)
    summary["drop_log_by_reason"] = _group_drop_log_by_reason(drop_log)
    summary["drop_log_by_source"] = _group_drop_log_by_source(drop_log)
    summary["repair_triggered"] = state.get("repair_request") is not None

    return EvaluatedSample(
        sample=sample,
        response=response,
        summary=summary,
        duration_ms=duration_ms,
        drop_log=drop_log,
        normalized_result=normalized_result,
    )


def _group_drop_log_by_stage(drop_log: list[DropLogEntry]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for entry in drop_log:
        counts[entry.drop_stage] += 1
    return dict(counts)


def _group_drop_log_by_reason(drop_log: list[DropLogEntry]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for entry in drop_log:
        counts[entry.drop_reason] += 1
    return dict(counts)


def _group_drop_log_by_source(drop_log: list[DropLogEntry]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for entry in drop_log:
        counts[entry.source_agent] += 1
    return dict(counts)


def _build_model_selection(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.model_preset:
        return {"preset": args.model_preset}
    if args.default_profile:
        return {"default_profile": args.default_profile}
    return None


def _build_usage_summary() -> dict[str, Any]:
    return {
        "available": False,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "per_agent": {},
        "aggregate": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        },
        "note": "run-local 当前未从 workflow 聚合到 usage；如已开启 LangSmith tracing，可在 trace 中查看真实 token。",
    }


def _normalize_usage_summary(raw_usage: dict[str, Any] | None) -> dict[str, Any]:
    if not raw_usage:
        return _build_usage_summary()
    if "aggregate" in raw_usage or "per_agent" in raw_usage:
        aggregate = raw_usage.get("aggregate", {}) or {}
        total_tokens = aggregate.get("total_tokens")
        return {
            "available": bool(raw_usage.get("available")) and total_tokens is not None,
            "input_tokens": aggregate.get("input_tokens"),
            "output_tokens": aggregate.get("output_tokens"),
            "total_tokens": total_tokens,
            "per_agent": raw_usage.get("per_agent", {}),
            "aggregate": aggregate,
            "note": raw_usage.get("note"),
        }
    input_tokens = raw_usage.get("input_tokens")
    output_tokens = raw_usage.get("output_tokens")
    total_tokens = raw_usage.get("total_tokens")
    return {
        "available": total_tokens is not None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "per_agent": {},
        "aggregate": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "input_token_details": raw_usage.get("input_token_details"),
        "output_token_details": raw_usage.get("output_token_details"),
        "note": raw_usage.get("note"),
    }


def _model_suffix(model_selection: dict[str, Any] | None) -> str:
    if not model_selection:
        return "default"
    if model_selection.get("default_profile"):
        return str(model_selection["default_profile"])
    if model_selection.get("preset"):
        return str(model_selection["preset"])
    return "custom"


def _sanitize_path_fragment(value: str) -> str:
    keep: list[str] = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("-")
    return "".join(keep).strip("-") or "default"


def _write_run_bundle(output_root: Path, evaluated_samples: list[EvaluatedSample], aggregate: dict[str, Any]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    sample_overview = [
        {
            "sample_id": item.summary["sample_id"],
            "passed": item.summary["passed"],
            "inline_mark_count": item.summary["inline_mark_count"],
            "sentence_entry_count": item.summary["sentence_entry_count"],
            "warning_count": item.summary["warning_count"],
            "translation_complete": item.summary["translation_complete"],
            "duration_ms": item.summary["duration_ms"],
            "request_id": item.summary["request_id"],
            "usage": item.summary["usage"],
            # V3: drop_log metrics
            "drop_log_count": item.summary.get("drop_log_count", 0),
            "repair_triggered": item.summary.get("repair_triggered", False),
        }
        for item in evaluated_samples
    ]
    (output_root / "summary.json").write_text(
        json.dumps(
            {
                "aggregate": aggregate,
                "samples": sample_overview,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    for item in evaluated_samples:
        (output_root / f"{item.sample.id}.response.json").write_text(
            json.dumps(_result_to_jsonable(item.response), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_root / f"{item.sample.id}.summary.json").write_text(
            json.dumps(item.summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # V3: Write drop_log if present
        if item.drop_log:
            drop_log_data = [d.model_dump(mode="json") for d in item.drop_log]
            (output_root / f"{item.sample.id}.drop_log.json").write_text(
                json.dumps(drop_log_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    # V3 aggregate drop_log stats
    total_drop_log = sum(item.summary.get("drop_log_count", 0) for item in evaluated_samples)
    repair_triggered_count = sum(1 for item in evaluated_samples if item.summary.get("repair_triggered", False))

    lines = [
        "# 回归测试摘要",
        "",
        "## 总览",
        "",
        f"- 数据集路径：`{aggregate['dataset_path']}`",
        f"- 样本总数：`{aggregate['total_samples']}`",
        f"- 通过样本：`{aggregate['passed_samples']}`",
        f"- 失败样本：`{aggregate['failed_samples']}`",
        f"- 模型选择：`{json.dumps(aggregate['model_selection'], ensure_ascii=False)}`",
        f"- LangSmith tracing 已开启：`{'是' if aggregate['langsmith_tracing_enabled'] else '否'}`",
        f"- 总耗时：`{aggregate['total_duration_ms']} ms`",
        f"- 平均耗时：`{aggregate['average_duration_ms']} ms`",
        f"- 含 token 数据的样本数：`{aggregate['usage_sample_count']}`",
        f"- 输入 tokens：`{aggregate['total_input_tokens'] if aggregate['total_input_tokens'] is not None else '-'}`",
        f"- 输出 tokens：`{aggregate['total_output_tokens'] if aggregate['total_output_tokens'] is not None else '-'}`",
        f"- 总 tokens：`{aggregate['total_tokens'] if aggregate['total_tokens'] is not None else '-'}`",
        # V3 new metrics
        f"- V3 drop_log 总数：`{total_drop_log}`",
        f"- V3 repair 触发次数：`{repair_triggered_count}`",
        "",
        "## 样本明细",
        "",
        "| sample_id | 结果 | inline_marks | sentence_entries | warnings | 耗时(ms) | 翻译覆盖 | drop_log | repair | tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in evaluated_samples:
        usage = item.summary.get("usage", {})
        token_display = (
            str(usage.get("total_tokens"))
            if usage.get("total_tokens") is not None
            else "-"
        )
        lines.append(
            f"| {item.sample.id} | {'通过' if item.summary['passed'] else '失败'} | "
            f"{item.summary['inline_mark_count']} | {item.summary['sentence_entry_count']} | "
            f"{item.summary['warning_count']} | {item.summary['duration_ms']} | "
            f"{'是' if item.summary['translation_complete'] else '否'} | "
            f"{item.summary.get('drop_log_count', 0)} | "
            f"{'是' if item.summary.get('repair_triggered') else '否'} | {token_display} |"
        )
    failed_samples = [item for item in evaluated_samples if not item.summary["passed"]]
    if failed_samples:
        lines.extend(["", "## 失败详情", ""])
        for item in failed_samples:
            summary = item.summary
            lines.append(f"### {item.sample.id}")
            lines.append(f"- 耗时：`{summary['duration_ms']} ms`")
            if summary["must_not_hit_failures"]:
                lines.append(f"- must_not_hit 误命中：`{len(summary['must_not_hit_failures'])}`")
            if summary["count_failures"]:
                lines.append(f"- 数量边界失败：`{json.dumps(summary['count_failures'], ensure_ascii=False)}`")
            if summary["warning_limit_failed"]:
                lines.append(
                    f"- warning 超标：`{summary['actual_warning_count']} > {summary['max_warning_count']}`"
                )
            if not summary["translation_complete"]:
                lines.append("- 翻译覆盖不完整")
            lines.append("")
    # V3 drop_log summary
    if total_drop_log > 0:
        lines.extend(["", "## V3 Drop Log 统计", ""])
        all_stages: dict[str, int] = defaultdict(int)
        all_reasons: dict[str, int] = defaultdict(int)
        all_sources: dict[str, int] = defaultdict(int)
        for item in evaluated_samples:
            for stage, count in item.summary.get("drop_log_by_stage", {}).items():
                all_stages[stage] += count
            for reason, count in item.summary.get("drop_log_by_reason", {}).items():
                all_reasons[reason] += count
            for source, count in item.summary.get("drop_log_by_source", {}).items():
                all_sources[source] += count
        lines.append("### 按阶段分布")
        for stage, count in sorted(all_stages.items()):
            lines.append(f"- {stage}: {count}")
        lines.append("### 按原因分布")
        for reason, count in sorted(all_reasons.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("### 按来源分布")
        for source, count in sorted(all_sources.items()):
            lines.append(f"- {source}: {count}")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 当前 `passed/failed` 只表示 contract gate 是否通过，不代表语义质量已经最佳。",
            "- 语义质量、讲解帮助度、标注取舍是否合理，建议另配 LLM-as-judge 或人工 spot check。",
            "- `run-local` 当前直接统计壁钟耗时。",
            "- token 字段来自 workflow 聚合 usage 摘要；若显示为 `-`，表示该次运行未拿到 usage。",
            "- 如已开启 LangSmith tracing，可在对应 trace 中查看 LLM usage 详情。",
            "- V3 drop_log 记录 normalize_and_ground 阶段的删除/降级操作。",
        ]
    )
    (output_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_local(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset).resolve()
    samples = load_samples(dataset_path)
    selected_ids = set(args.sample_ids or [])
    if selected_ids:
        samples = [sample for sample in samples if sample.id in selected_ids]
        if not samples:
            print(
                json.dumps(
                    {
                        "dataset_path": str(dataset_path),
                        "error": "no_matching_samples",
                        "requested_sample_ids": sorted(selected_ids),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2
    model_selection = _build_model_selection(args)
    evaluated_samples: list[EvaluatedSample] = []
    print(
        f"[回归] 开始执行，共 {len(samples)} 个样本；模型={json.dumps(model_selection, ensure_ascii=False) if model_selection else 'default'}"
    )
    for index, sample in enumerate(samples, start=1):
        print(f"[回归] ({index}/{len(samples)}) 开始：{sample.id}")
        evaluated = await _run_sample(sample, model_selection)
        evaluated_samples.append(evaluated)
        print(
            f"[回归] ({index}/{len(samples)}) 完成：{sample.id} | "
            f"{'通过' if evaluated.summary['passed'] else '失败'} | "
            f"{evaluated.duration_ms} ms | warnings={evaluated.summary['warning_count']}"
        )
    passed_samples = sum(1 for item in evaluated_samples if item.summary["passed"])
    total_duration_ms = sum(item.duration_ms for item in evaluated_samples)
    average_duration_ms = int(total_duration_ms / len(evaluated_samples)) if evaluated_samples else 0
    usage_items = [item.summary.get("usage", {}) for item in evaluated_samples]
    usable_usage_items = [item for item in usage_items if item.get("total_tokens") is not None]
    aggregate = {
        "dataset_path": str(dataset_path),
        "total_samples": len(evaluated_samples),
        "passed_samples": passed_samples,
        "failed_samples": len(evaluated_samples) - passed_samples,
        "model_selection": model_selection,
        "langsmith_tracing_enabled": bool(os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")),
        "total_duration_ms": total_duration_ms,
        "average_duration_ms": average_duration_ms,
        "usage_sample_count": len(usable_usage_items),
        "total_input_tokens": sum(item.get("input_tokens", 0) for item in usable_usage_items) if usable_usage_items else None,
        "total_output_tokens": sum(item.get("output_tokens", 0) for item in usable_usage_items) if usable_usage_items else None,
        "total_tokens": sum(item.get("total_tokens", 0) for item in usable_usage_items) if usable_usage_items else None,
    }
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    profile_suffix = _sanitize_path_fragment(_model_suffix(model_selection))
    output_root_base = Path(args.output_dir).resolve()
    if args.mark:
        output_root = output_root_base / args.mark / f"{timestamp}-{profile_suffix}"
    else:
        output_root = output_root_base / f"{timestamp}-{profile_suffix}"
    _write_run_bundle(output_root, evaluated_samples, aggregate)
    print(json.dumps({"output_dir": str(output_root), **aggregate}, ensure_ascii=False, indent=2))
    return 0 if aggregate["failed_samples"] == 0 else 1


def _to_langsmith_examples(samples: list[RegressionSample]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for sample in samples:
        examples.append(
            {
                "inputs": {
                    "sample_id": sample.id,
                    **sample.inputs.model_dump(mode="json"),
                },
                "outputs": {
                    "description": sample.description,
                    "expectations": sample.expectations.model_dump(mode="json"),
                },
                "metadata": {"sample_id": sample.id, "source": "local_regression_suite"},
            }
        )
    return examples


def sync_langsmith(args: argparse.Namespace) -> int:
    from langsmith import Client

    dataset_path = Path(args.dataset).resolve()
    samples = load_samples(dataset_path)
    examples = _to_langsmith_examples(samples)
    client = Client()
    dataset_name = args.dataset_name
    try:
        existing = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        existing = None
    if existing is not None and args.replace:
        client.delete_dataset(dataset_id=existing.id)
        existing = None
    if existing is None:
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="Claread workflow 本地固定回归集（用于输出质量回归，不属于生产主链）",
            metadata={"source_path": str(dataset_path)},
        )
    else:
        dataset = existing
    client.create_examples(dataset_id=dataset.id, examples=examples)
    print(json.dumps({"dataset_name": dataset_name, "dataset_id": str(dataset.id), "example_count": len(examples)}, ensure_ascii=False, indent=2))
    return 0


def run_langsmith(args: argparse.Namespace) -> int:
    from langsmith.evaluation import evaluate

    dataset_path = Path(args.dataset).resolve()
    samples = load_samples(dataset_path)
    sample_map = {sample.id: sample for sample in samples}
    data = _to_langsmith_examples(samples)
    model_selection = _build_model_selection(args)

    def run_workflow(inputs: dict[str, Any]) -> dict[str, Any]:
        sample_id = inputs["sample_id"]
        sample = sample_map[sample_id]
        evaluated = asyncio.run(_run_sample(sample, model_selection))
        return {
            "response": _result_to_jsonable(evaluated.response),
            "summary": evaluated.summary,
            # V3: Include drop_log and repair info for evaluators
            "drop_log": [d.model_dump(mode="json") for d in evaluated.drop_log],
            "repair_triggered": evaluated.summary.get("repair_triggered", False),
        }

    def schema_valid_evaluator(run, example):
        outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
        try:
            RenderSceneModel.model_validate(outputs.get("response", {}))
            return {"score": 1, "comment": "response schema valid"}
        except Exception as exc:
            return {"score": 0, "comment": f"schema invalid: {type(exc).__name__}"}

    def must_not_hit_evaluator(run, example):
        outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
        summary = outputs.get("summary", {})
        failures = summary.get("must_not_hit_failures", [])
        return {"score": 1 if not failures else 0, "comment": f"must_not_hit_failures={len(failures)}"}

    def translation_coverage_evaluator(run, example):
        outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
        summary = outputs.get("summary", {})
        return {
            "score": 1 if summary.get("translation_complete") else 0,
            "comment": f"translation_complete={summary.get('translation_complete')}",
        }

    def drop_log_evaluator(run, example):
        """V3: Evaluate drop_log metrics from normalize_and_ground stage."""
        outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
        drop_log = outputs.get("drop_log", [])
        drop_log_count = len(drop_log)

        # Evaluate drop log health
        # High drop rate might indicate agent quality issues
        summary = outputs.get("summary", {})
        inline_mark_count = summary.get("inline_mark_count", 0)

        # Calculate drop rate
        if inline_mark_count + drop_log_count > 0:
            drop_rate = drop_log_count / (inline_mark_count + drop_log_count)
        else:
            drop_rate = 0.0

        # Score: penalize if drop rate > 50% (indicates poor agent output)
        if drop_rate > 0.5:
            score = 0
            comment = f"high_drop_rate={drop_rate:.2%} drop_count={drop_log_count}"
        elif drop_rate > 0.3:
            score = 0.5
            comment = f"moderate_drop_rate={drop_rate:.2%} drop_count={drop_log_count}"
        else:
            score = 1
            comment = f"drop_rate={drop_rate:.2%} drop_count={drop_log_count}"

        return {"score": score, "comment": comment}

    def repair_log_evaluator(run, example):
        """V3: Evaluate whether repair was triggered and succeeded."""
        outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
        repair_triggered = outputs.get("repair_triggered", False)

        # If repair wasn't triggered, that's fine (score=1)
        # If repair was triggered but overall passed, also fine
        summary = outputs.get("summary", {})
        passed = summary.get("passed", False)

        if not repair_triggered:
            return {"score": 1, "comment": "repair_not_needed"}
        else:
            # Repair was triggered - this might indicate issues but isn't necessarily bad
            if passed:
                return {"score": 1, "comment": "repair_triggered_and_fixed"}
            else:
                return {"score": 0.5, "comment": "repair_triggered_but_still_failing"}

    results = evaluate(
        run_workflow,
        data=data,
        evaluators=[
            schema_valid_evaluator,
            must_not_hit_evaluator,
            translation_coverage_evaluator,
            drop_log_evaluator,
            repair_log_evaluator,
        ],
        experiment_prefix=args.experiment_prefix,
        metadata={"source": "local_regression_suite", "model_selection": model_selection or {}},
        upload_results=True,
    )
    print(json.dumps({"experiment_prefix": args.experiment_prefix, "result_type": type(results).__name__}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Claread workflow 本地回归集工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_flags(target: argparse.ArgumentParser) -> None:
        target.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="本地回归集 JSON 路径")
        target.add_argument("--model-preset", help="使用 server preset 运行样本")
        target.add_argument("--default-profile", help="直接覆盖默认 model profile")

    run_local_parser = subparsers.add_parser("run-local", help="本地执行回归集并产出报告")
    add_common_flags(run_local_parser)
    run_local_parser.add_argument("--sample-id", dest="sample_ids", action="append", help="只运行指定 sample_id，可重复传入")
    run_local_parser.add_argument("--output-dir", default=str(DEFAULT_RUNS_DIR), help="本地输出目录")
    run_local_parser.add_argument("--mark", help="输出目录名称前缀")
    run_local_parser.set_defaults(handler=run_local)

    sync_parser = subparsers.add_parser("sync-langsmith", help="把本地回归集同步到 LangSmith dataset")
    add_common_flags(sync_parser)
    sync_parser.add_argument("--dataset-name", required=True, help="LangSmith dataset 名称")
    sync_parser.add_argument("--replace", action="store_true", help="若 dataset 已存在，则先删除再重建")
    sync_parser.set_defaults(handler=sync_langsmith)

    evaluate_parser = subparsers.add_parser("run-langsmith", help="用 LangSmith evaluate 跑本地回归集实验")
    add_common_flags(evaluate_parser)
    evaluate_parser.add_argument("--experiment-prefix", required=True, help="LangSmith experiment 前缀")
    evaluate_parser.set_defaults(handler=run_langsmith)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handler = args.handler
    if asyncio.iscoroutinefunction(handler):
        return asyncio.run(handler(args))
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

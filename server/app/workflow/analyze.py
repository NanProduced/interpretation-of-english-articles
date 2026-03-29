from __future__ import annotations

import re
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.core_v0 import CoreAgentDeps, run_core_agent
from app.agents.translation_v0 import TranslationAgentDeps, run_translation_agent
from app.schemas.analysis import (
    AnalysisAnnotations,
    AnalysisMetrics,
    AnalysisResult,
    AnalysisStatus,
    AnalysisTranslations,
    AnalysisWarning,
    AnalyzeRequest,
    AnalyzeRequestMeta,
    ArticleParagraph,
    ArticleSentence,
    ArticleStructure,
    CoreAgentOutput,
    DifficultSentenceAnnotation,
    DifficultSentenceChunk,
    GrammarAnnotation,
    KeyPhraseTranslation,
    SentenceComponent,
    SentenceDifficultyAssessment,
    SentenceTranslation,
    TranslationAgentOutput,
    VocabularyAnnotation,
)
from app.schemas.preprocess import PreprocessResult, TextSpan
from app.schemas.preprocess import PreprocessAnalyzeRequest
from app.workflow.preprocess import run_preprocess_v0


WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]{3,}\b")
COMMON_WORDS = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "they",
    "their",
    "there",
    "which",
    "while",
    "would",
    "about",
    "could",
    "these",
    "those",
    "into",
    "than",
    "because",
    "through",
}


class AnalyzeState(TypedDict, total=False):
    # 这是 analyze_v0 在 LangGraph 节点之间传递的共享状态。
    payload: AnalyzeRequest
    preprocess: PreprocessResult
    route_decision: Literal["continue", "reject"]
    core_output: CoreAgentOutput
    translation_output: TranslationAgentOutput
    warnings: list[AnalysisWarning]
    status: AnalysisStatus
    merged_result: AnalysisResult
    result: AnalysisResult


def _build_article(preprocess: PreprocessResult, difficulties: list[SentenceDifficultyAssessment]) -> ArticleStructure:
    # 这里把 preprocess 的切分结果提升成最终 article 结构，后续前端就以它为正文锚点。
    difficulty_map = {item.sentence_id: item for item in difficulties}
    paragraphs: list[ArticleParagraph] = []
    for paragraph in preprocess.segmentation.paragraphs:
        sentence_ids = [
            sentence.sentence_id
            for sentence in preprocess.segmentation.sentences
            if sentence.paragraph_id == paragraph.paragraph_id
        ]
        paragraphs.append(
            ArticleParagraph(
                paragraph_id=paragraph.paragraph_id,
                text=paragraph.text,
                start=paragraph.start,
                end=paragraph.end,
                sentence_ids=sentence_ids,
            )
        )

    sentences: list[ArticleSentence] = []
    for sentence in preprocess.segmentation.sentences:
        difficulty = difficulty_map.get(
            sentence.sentence_id,
            SentenceDifficultyAssessment(
                sentence_id=sentence.sentence_id,
                difficulty_score=0.3,
                is_difficult=False,
            ),
        )
        sentences.append(
            ArticleSentence(
                sentence_id=sentence.sentence_id,
                paragraph_id=sentence.paragraph_id,
                text=sentence.text,
                start=sentence.start,
                end=sentence.end,
                difficulty_score=difficulty.difficulty_score,
                is_difficult=difficulty.is_difficult,
            )
        )

    return ArticleStructure(
        source_type=preprocess.request.source_type,
        source_text=preprocess.normalized.source_text,
        render_text=preprocess.normalized.clean_text,
        paragraphs=paragraphs,
        sentences=sentences,
    )


def _priority_by_profile(profile_key: str, objective_level: str) -> Literal["core", "expand", "reference"]:
    if profile_key.startswith("exam"):
        if objective_level == "basic":
            return "core"
        if objective_level == "intermediate":
            return "core"
        return "expand"

    if profile_key in {"ielts", "toefl"}:
        if objective_level == "advanced":
            return "core"
        return "expand"

    if objective_level == "basic":
        return "expand"
    return "reference"


def _default_visible_by_priority(priority: str) -> bool:
    return priority == "core"


def _find_span(render_text: str, snippet: str) -> TextSpan | None:
    if not snippet:
        return None
    start = render_text.find(snippet)
    if start < 0:
        return None
    return TextSpan(start=start, end=start + len(snippet))


def _fallback_core(preprocess: PreprocessResult, profile_key: str) -> CoreAgentOutput:
    # 这是本地规则兜底，只保证“结构完整可调试”，不追求最终标注质量。
    render_text = preprocess.normalized.clean_text
    sentence_difficulties: list[SentenceDifficultyAssessment] = []
    vocabulary: list[VocabularyAnnotation] = []
    grammar: list[GrammarAnnotation] = []
    difficult_sentences: list[DifficultSentenceAnnotation] = []

    for sentence in preprocess.segmentation.sentences:
        words = WORD_PATTERN.findall(sentence.text)
        is_difficult = len(words) >= 18 or "," in sentence.text or " which " in sentence.text.lower()
        score = 0.78 if is_difficult else 0.32
        sentence_difficulties.append(
            SentenceDifficultyAssessment(
                sentence_id=sentence.sentence_id,
                difficulty_score=score,
                is_difficult=is_difficult,
            )
        )

    candidate_words: list[tuple[str, str, TextSpan]] = []
    for sentence in preprocess.segmentation.sentences:
        for match in WORD_PATTERN.finditer(sentence.text):
            word = match.group(0)
            normalized = word.lower()
            if normalized in COMMON_WORDS or len(normalized) < 6:
                continue
            absolute_start = sentence.start + match.start()
            span = TextSpan(start=absolute_start, end=absolute_start + len(word))
            candidate_words.append((sentence.sentence_id, word, span))

    for index, (sentence_id, surface, span) in enumerate(candidate_words[:8], start=1):
        vocabulary.append(
            VocabularyAnnotation(
                annotation_id=f"v{index}",
                surface=surface,
                lemma=surface.lower(),
                span=span,
                sentence_id=sentence_id,
                phrase_type="word",
                context_gloss_zh=f"{surface} 在当前语境中是需要重点关注的词。",
                short_explanation_zh="这是 fallback 生成的简化说明，后续会由正式 agent 提供更稳定解释。",
                objective_level="intermediate" if len(surface) >= 8 else "basic",
                priority="core" if profile_key.startswith("exam") else "expand",
                default_visible=True,
            )
        )

    grammar_index = 1
    for sentence in preprocess.segmentation.sentences:
        lowered = sentence.text.lower()
        if " which " in lowered or " that " in lowered:
            grammar.append(
                GrammarAnnotation(
                    annotation_id=f"g{grammar_index}",
                    type="grammar_point",
                    sentence_id=sentence.sentence_id,
                    span=TextSpan(start=sentence.start, end=sentence.end),
                    label="从句结构",
                    short_explanation_zh="该句包含从句或修饰性结构，阅读时建议先抓主干。",
                    objective_level="intermediate",
                    priority="core",
                    default_visible=False,
                )
            )
            grammar_index += 1

        parts = sentence.text.split(" ", 2)
        if len(parts) >= 2:
            subject_text = " ".join(parts[:1])
            predicate_text = parts[1]
            grammar.append(
                GrammarAnnotation(
                    annotation_id=f"g{grammar_index}",
                    type="sentence_component",
                    sentence_id=sentence.sentence_id,
                    label="句子主干",
                    short_explanation_zh="这里先用简化规则标出主语和谓语，后续会由正式 agent 细化。",
                    components=[
                        SentenceComponent(
                            label="subject",
                            text=subject_text,
                            span=_find_span(render_text, subject_text),
                        ),
                        SentenceComponent(
                            label="predicate",
                            text=predicate_text,
                            span=_find_span(render_text, predicate_text),
                        ),
                    ],
                    objective_level="basic",
                    priority="expand",
                    default_visible=False,
                )
            )
            grammar_index += 1

    difficult_index = 1
    for item in sentence_difficulties:
        if not item.is_difficult:
            continue
        sentence = next(
            current for current in preprocess.segmentation.sentences if current.sentence_id == item.sentence_id
        )
        chunks = [
            DifficultSentenceChunk(order=order, label=f"意群 {order}", text=chunk.strip())
            for order, chunk in enumerate(sentence.text.split(","), start=1)
            if chunk.strip()
        ]
        difficult_sentences.append(
            DifficultSentenceAnnotation(
                annotation_id=f"d{difficult_index}",
                sentence_id=sentence.sentence_id,
                span=TextSpan(start=sentence.start, end=sentence.end),
                trigger_reason=["long_sentence"] if len(sentence.text.split()) >= 18 else ["embedded_clause"],
                main_clause=chunks[0].text if chunks else sentence.text,
                chunks=chunks or [DifficultSentenceChunk(order=1, label="主干", text=sentence.text)],
                reading_path_zh="先看句子主干，再按逗号或从句边界拆开理解。",
                objective_level="intermediate",
                priority="core",
                default_visible=True,
            )
        )
        difficult_index += 1

    return CoreAgentOutput(
        sentence_difficulties=sentence_difficulties,
        vocabulary=vocabulary,
        grammar=grammar,
        difficult_sentences=difficult_sentences,
    )


def _fallback_translation(preprocess: PreprocessResult) -> TranslationAgentOutput:
    sentence_translations = [
        SentenceTranslation(
            sentence_id=sentence.sentence_id,
            translation_zh=f"【待优化翻译】{sentence.text}",
            style="natural",
        )
        for sentence in preprocess.segmentation.sentences
    ]

    key_phrase_translations: list[KeyPhraseTranslation] = []
    for sentence in preprocess.segmentation.sentences[:3]:
        words = WORD_PATTERN.findall(sentence.text)
        if not words:
            continue
        phrase = words[0]
        span = _find_span(preprocess.normalized.clean_text, phrase)
        if span is None:
            continue
        key_phrase_translations.append(
            KeyPhraseTranslation(
                phrase=phrase,
                sentence_id=sentence.sentence_id,
                span=span,
                translation_zh=f"{phrase}（待补充）",
            )
        )

    return TranslationAgentOutput(
        sentence_translations=sentence_translations,
        full_translation_zh="【待优化翻译】当前使用 fallback 翻译结果，后续会由正式翻译 agent 输出自然中文。",
        key_phrase_translations=key_phrase_translations,
    )


async def preprocess_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    preprocess = await run_preprocess_v0(
        PreprocessAnalyzeRequest(
            text=payload.text,
            profile_key=payload.profile_key,
            source_type=payload.source_type,
            request_id=payload.request_id,
        )
    )
    warnings = [
        AnalysisWarning(code=item.code, message_zh=item.message_zh)
        for item in preprocess.warnings
    ]
    return {"preprocess": preprocess, "warnings": warnings}


async def router_node(state: AnalyzeState) -> AnalyzeState:
    preprocess = state["preprocess"]
    if preprocess.routing.decision == "reject":
        return {
            "route_decision": "reject",
            "status": AnalysisStatus(
                state="failed",
                degraded=True,
                error_code="PREPROCESS_REJECTED",
                user_message="输入文本未通过预处理校验，暂不进入完整标注流程。",
            ),
        }

    degraded = preprocess.routing.decision == "degraded"
    return {
        "route_decision": "continue",
        "status": AnalysisStatus(
            state="success",
            degraded=degraded,
            error_code=None,
            user_message="已完成完整解读。",
        ),
    }


async def core_node(state: AnalyzeState) -> AnalyzeState:
    preprocess = state["preprocess"]
    payload = state["payload"]
    deps = CoreAgentDeps(
        profile_key=payload.profile_key,
        render_text=preprocess.normalized.clean_text,
        paragraphs=[paragraph.model_dump() for paragraph in preprocess.segmentation.paragraphs],
        sentences=[sentence.model_dump() for sentence in preprocess.segmentation.sentences],
    )
    try:
        output = await run_core_agent(deps)
        return {"core_output": output}
    except Exception:
        # 先保证整条链路可返回，再通过 warning 明确告诉调用方这里走了 fallback。
        warnings = list(state.get("warnings", []))
        warnings.append(
            AnalysisWarning(
                code="CORE_AGENT_FALLBACK",
                message_zh="核心标注 agent 调用失败，当前已回退到本地规则结果。",
            )
        )
        status = state["status"].model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "核心标注部分使用了 fallback 结果。",
            }
        )
        return {
            "core_output": _fallback_core(preprocess, payload.profile_key),
            "warnings": warnings,
            "status": status,
        }


async def translation_node(state: AnalyzeState) -> AnalyzeState:
    preprocess = state["preprocess"]
    payload = state["payload"]
    deps = TranslationAgentDeps(
        profile_key=payload.profile_key,
        render_text=preprocess.normalized.clean_text,
        sentences=[sentence.model_dump() for sentence in preprocess.segmentation.sentences],
    )
    try:
        output = await run_translation_agent(deps)
        return {"translation_output": output}
    except Exception:
        warnings = list(state.get("warnings", []))
        warnings.append(
            AnalysisWarning(
                code="TRANSLATION_AGENT_FALLBACK",
                message_zh="翻译 agent 调用失败，当前已回退到本地规则结果。",
            )
        )
        status = state["status"].model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "翻译部分使用了 fallback 结果。",
            }
        )
        return {
            "translation_output": _fallback_translation(preprocess),
            "warnings": warnings,
            "status": status,
        }


async def merge_node(state: AnalyzeState) -> AnalyzeState:
    # 先把 core 和 translation 两个分支的结果合并成统一结果对象。
    preprocess = state["preprocess"]
    article = _build_article(preprocess, state["core_output"].sentence_difficulties)
    annotations = AnalysisAnnotations(
        vocabulary=state["core_output"].vocabulary,
        grammar=state["core_output"].grammar,
        difficult_sentences=state["core_output"].difficult_sentences,
    )
    translations = AnalysisTranslations(
        sentence_translations=state["translation_output"].sentence_translations,
        full_translation_zh=state["translation_output"].full_translation_zh,
        key_phrase_translations=state["translation_output"].key_phrase_translations,
    )
    result = AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=preprocess.request.request_id,
            profile_key=preprocess.request.profile_key,
            source_type=preprocess.request.source_type,
            discourse_enabled=state["payload"].discourse_enabled,
        ),
        status=state["status"],
        article=article,
        annotations=annotations,
        translations=translations,
        warnings=state.get("warnings", []),
        metrics=AnalysisMetrics(
            vocabulary_count=len(annotations.vocabulary),
            grammar_count=len(annotations.grammar),
            difficult_sentence_count=len(annotations.difficult_sentences),
            sentence_count=len(article.sentences),
            paragraph_count=len(article.paragraphs),
        ),
    )
    return {"merged_result": result}


async def enrich_node(state: AnalyzeState) -> AnalyzeState:
    # 这里先做最小 profile 富化：根据 profile 调整优先级和默认展示层级。
    result = state["merged_result"].model_copy(deep=True)
    profile_key = result.request.profile_key

    for item in result.annotations.vocabulary:
        item.priority = _priority_by_profile(profile_key, item.objective_level)
        item.default_visible = _default_visible_by_priority(item.priority)

    for item in result.annotations.grammar:
        item.priority = _priority_by_profile(profile_key, item.objective_level)
        item.default_visible = _default_visible_by_priority(item.priority)

    for item in result.annotations.difficult_sentences:
        item.priority = _priority_by_profile(profile_key, item.objective_level)
        item.default_visible = _default_visible_by_priority(item.priority)

    return {"merged_result": result}


async def validate_node(state: AnalyzeState) -> AnalyzeState:
    # 输出校验先做最小规则，确保前端能稳定消费，不合格时直接打 warning 并降级状态。
    result = state["merged_result"].model_copy(deep=True)
    warnings = list(result.warnings)

    sentence_ids = {sentence.sentence_id for sentence in result.article.sentences}
    translation_ids = {item.sentence_id for item in result.translations.sentence_translations}

    if translation_ids != sentence_ids:
        warnings.append(
            AnalysisWarning(
                code="TRANSLATION_COVERAGE_MISMATCH",
                message_zh="逐句翻译未完整覆盖全部句子，当前结果存在缺口。",
            )
        )
        result.status = result.status.model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "部分输出未通过完整校验，请结合原文查看。",
            }
        )

    for collection_name in ("vocabulary", "grammar", "difficult_sentences"):
        items = getattr(result.annotations, collection_name)
        for item in items:
            if getattr(item, "sentence_id", None) not in sentence_ids:
                warnings.append(
                    AnalysisWarning(
                        code="INVALID_SENTENCE_REFERENCE",
                        message_zh=f"{collection_name} 中存在无法映射到正文句子的标注，已保留原始结果供排查。",
                    )
                )
                result.status = result.status.model_copy(
                    update={
                        "state": "partial_success",
                        "degraded": True,
                        "user_message": "部分标注未通过引用校验，请结合原文查看。",
                    }
                )
                break

    result.warnings = warnings
    return {"result": AnalysisResult.model_validate(result.model_dump())}


async def finalize_success_node(state: AnalyzeState) -> AnalyzeState:
    return {"result": state["result"]}


async def finalize_rejected_node(state: AnalyzeState) -> AnalyzeState:
    # 如果 preprocess 已经判断不应继续，就返回一个结构完整但内容为空的失败结果。
    preprocess = state["preprocess"]
    article = _build_article(preprocess, [])
    result = AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=preprocess.request.request_id,
            profile_key=preprocess.request.profile_key,
            source_type=preprocess.request.source_type,
            discourse_enabled=state["payload"].discourse_enabled,
        ),
        status=state["status"],
        article=article,
        annotations=AnalysisAnnotations(),
        translations=AnalysisTranslations(
            sentence_translations=[],
            full_translation_zh="",
            key_phrase_translations=[],
        ),
        warnings=state.get("warnings", []),
        metrics=AnalysisMetrics(
            vocabulary_count=0,
            grammar_count=0,
            difficult_sentence_count=0,
            sentence_count=len(article.sentences),
            paragraph_count=len(article.paragraphs),
        ),
    )
    return {"result": result}


def _route_after_router(state: AnalyzeState) -> Literal["core", "rejected"]:
    return "rejected" if state["route_decision"] == "reject" else "core"


def build_analyze_graph():
    # 当前 analyze_v0 已覆盖最小完整链路：预处理 -> Router -> 核心标注 -> 翻译 -> 合并 -> 富化 -> 校验。
    graph = StateGraph(AnalyzeState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("router", router_node)
    graph.add_node("core", core_node)
    graph.add_node("translation", translation_node)
    graph.add_node("merge", merge_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("validate", validate_node)
    graph.add_node("finalize_success", finalize_success_node)
    graph.add_node("finalize_rejected", finalize_rejected_node)

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "router")
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "core": "core",
            "rejected": "finalize_rejected",
        },
    )
    graph.add_edge("core", "translation")
    graph.add_edge("translation", "merge")
    graph.add_edge("merge", "enrich")
    graph.add_edge("enrich", "validate")
    graph.add_edge("validate", "finalize_success")
    graph.add_edge("finalize_success", END)
    graph.add_edge("finalize_rejected", END)
    return graph.compile()


async def run_analyze_v0(payload: AnalyzeRequest) -> AnalysisResult:
    graph = build_analyze_graph()
    result = await graph.ainvoke({"payload": payload})
    return result["result"]

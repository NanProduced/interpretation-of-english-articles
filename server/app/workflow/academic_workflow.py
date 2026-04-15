from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.workflow.academic_nodes import (
    academic_translation_agent_node,
    assemble_academic_result_node,
    normalize_academic_node,
    parallel_academic_agents_node,
    project_academic_scene_node,
    structure_agent_node,
)
from app.workflow.academic_state import AcademicState
from app.workflow.analyze_nodes import (
    derive_user_config_node,
    prepare_input_node,
)


def build_academic_graph() -> Any:
    """Academic 拓扑模式。

    设计原则：
    1. 独立于 learning 拓扑，不复用 vocabulary/grammar/translation 三分法
    2. 按"术语/概念"、"逻辑/结构"、"解释/释义"、"全文综合"重新组织
    3. 输出协议围绕内容理解辅助，而非语言点标注

    工作流拓扑：
    START -> prepare_input -> derive_user_config -> parallel_academic_agents (term + logic + interpretation)
                                                         -> structure_agent (段落功能 + 全文摘要)
                                                         -> academic_translation_agent
           -> normalize_academic -> project_academic_scene -> assemble_academic_result -> END
    """
    graph = StateGraph(AcademicState)

    graph.add_node("prepare_input", prepare_input_node)
    graph.add_node("derive_user_config", derive_user_config_node)

    graph.add_node("parallel_academic_agents", parallel_academic_agents_node)
    graph.add_node("structure_agent", structure_agent_node)
    graph.add_node("academic_translation_agent", academic_translation_agent_node)

    graph.add_node("normalize_academic", normalize_academic_node)
    graph.add_node("project_academic_scene", project_academic_scene_node)
    graph.add_node("assemble_academic_result", assemble_academic_result_node)

    graph.add_edge(START, "prepare_input")
    graph.add_edge("prepare_input", "derive_user_config")

    graph.add_edge("derive_user_config", "parallel_academic_agents")
    graph.add_edge("derive_user_config", "structure_agent")
    graph.add_edge("derive_user_config", "academic_translation_agent")

    graph.add_edge("parallel_academic_agents", "normalize_academic")
    graph.add_edge("structure_agent", "normalize_academic")
    graph.add_edge("academic_translation_agent", "normalize_academic")

    graph.add_edge("normalize_academic", "project_academic_scene")
    graph.add_edge("project_academic_scene", "assemble_academic_result")
    graph.add_edge("assemble_academic_result", END)

    return graph.compile()

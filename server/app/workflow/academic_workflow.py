from __future__ import annotations

from typing import Any


class AcademicWorkflowNotImplementedError(RuntimeError):
    """Academic 拓扑尚未实现时的受控异常。"""


def build_academic_graph() -> Any:
    """Academic 拓扑模式占位。"""
    raise AcademicWorkflowNotImplementedError(
        "Academic topology mode is not yet implemented."
    )

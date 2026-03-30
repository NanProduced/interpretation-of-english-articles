from __future__ import annotations

from typing import Literal


def priority_by_profile(profile_key: str, objective_level: str) -> Literal["core", "expand", "reference"]:
    if profile_key.startswith("exam"):
        if objective_level in {"basic", "intermediate"}:
            return "core"
        return "expand"

    if profile_key in {"ielts", "toefl"}:
        if objective_level == "advanced":
            return "core"
        return "expand"

    if objective_level == "basic":
        return "expand"
    return "reference"


def default_visible_by_priority(priority: str) -> bool:
    return priority == "core"


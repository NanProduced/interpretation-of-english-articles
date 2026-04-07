"""
ECDICT 数据库查询模块（PostgreSQL 版本）。

本文件保留 EntryRow dataclass 定义以保持对其他模块的接口兼容，
查询实现已迁移至 app.services.dictionary.db_pg。
后续所有查询调用应直接 import db_pg。
"""

from __future__ import annotations

from app.services.dictionary.db_pg import (
    EntryRow,
    exact_lookup,
    full_lookup,
    lemma_lookup,
)

__all__ = ["EntryRow", "exact_lookup", "full_lookup", "lemma_lookup"]

"""
字典查询专用 spaCy Pipeline。
包含 tagger、lemmatizer 和 parser，用于句子分析和依存关系判断。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_dict_spacy_available: Optional[bool] = None
_dict_spacy_checked: bool = False
_dict_nlp = None

def check_dict_spacy_model() -> bool:
    global _dict_spacy_available, _dict_spacy_checked
    if _dict_spacy_checked:
        return bool(_dict_spacy_available)
    _dict_spacy_checked = True
    try:
        import spacy
        import spacy.util
        if not spacy.util.is_package("en_core_web_sm"):
            _dict_spacy_available = False
            logger.warning("dict: spaCy model en_core_web_sm unavailable. Falling back to exact/n-gram lookup. Install with: python -m spacy download en_core_web_sm")
        else:
            _dict_spacy_available = True
    except ImportError:
        _dict_spacy_available = False
        logger.warning("dict: spaCy package unavailable. Falling back to exact/n-gram lookup.")
    return bool(_dict_spacy_available)

def get_dict_nlp():
    """Lazy-load spaCy model. MUST only be called after check_dict_spacy_model() returns True."""
    global _dict_nlp
    if _dict_nlp is None:
        import spacy
        # 不禁用 parser 和 tagger，因为需要基于 DEP 和 POS 来判断 noun chunk 和 sb/sth 槽位
        _dict_nlp = spacy.load("en_core_web_sm", disable=["ner"])
    return _dict_nlp

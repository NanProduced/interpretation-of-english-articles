"""
围绕点击锚点生成候选形式：字面形式、词元形式和模板形式。
"""
from app.services.dictionary.nlp import check_dict_spacy_model, get_dict_nlp
from app.services.dictionary.phrase_templates import canonicalize_sentence_span
import logging

logger = logging.getLogger(__name__)

def generate_candidates(query: str, context_sentence: str, occurrence: int | None) -> list[str]:
    """
    基于 spaCy 的解析树，生成候选的短语 form 列表。
    """
    forms = []
    
    if not context_sentence:
        return forms

    try:
        if not check_dict_spacy_model():
            return forms

        nlp = get_dict_nlp()
        doc = nlp(context_sentence)
        
        # 寻找匹配 query 的 token
        target_tokens = [t for t in doc if t.text.lower() == query.lower() or t.lemma_.lower() == query.lower()]
        
        if not target_tokens:
            return forms
            
        if occurrence is not None and 1 <= occurrence <= len(target_tokens):
            target = target_tokens[occurrence - 1]
        elif len(target_tokens) == 1:
            target = target_tokens[0]
        else:
            return forms

        # Helper 添加 form 
        def add_span_forms(span):
            literal = span.text.lower()
            lemma_form = " ".join([t.lemma_.lower() for t in span])
            template_form = canonicalize_sentence_span(span, {target.i})
            
            if literal != query.lower():
                forms.append(literal)
            if lemma_form != literal and lemma_form != query.lower():
                forms.append(lemma_form)
            if template_form != lemma_form and template_form != literal and template_form != query.lower():
                forms.append(template_form)

        # 1. target 的完整子树
        subtree = list(target.subtree)
        if len(subtree) > 1:
            subtree.sort(key=lambda x: x.i)
            span = doc[subtree[0].i : subtree[-1].i + 1]
            add_span_forms(span)
                
        # 2. General Verb Phrase Extractor
        verb_head = None
        if target.pos_ in ("VERB", "AUX"):
            verb_head = target
        elif target.head and target.head.pos_ in ("VERB", "AUX"):
            verb_head = target.head
            
        if verb_head:
            # Full relaxed phrase
            valid_deps = {"prt", "prep", "dobj", "dative", "advmod", "acomp", "attr"}
            phrase_tokens = [verb_head]
            for child in verb_head.children:
                if child.dep_ in valid_deps:
                    phrase_tokens.append(child)
                    if child.dep_ == "prep":
                        phrase_tokens.extend([c for c in child.children if c.dep_ in ("pobj", "pcomp")])
            
            if target in phrase_tokens:
                phrase_tokens.sort(key=lambda t: t.i)
                span = doc[phrase_tokens[0].i : phrase_tokens[-1].i + 1]
                add_span_forms(span)
                
            # Strict core phrase: only include target + prep + dobj + prt
            core_deps = {"prt", "prep", "dobj", "dative", "acomp"}
            strict_tokens = [verb_head]
            if target not in strict_tokens:
                strict_tokens.append(target)
                
            for child in verb_head.children:
                if child.dep_ in core_deps and child not in strict_tokens:
                    strict_tokens.append(child)
                    if child.dep_ == "prep":
                        strict_tokens.extend([c for c in child.children if c.dep_ in ("pobj", "pcomp")])
            
            strict_tokens.sort(key=lambda t: t.i)
            # Find contiguous span if possible, or just generate tokens manually
            # But add_span_forms takes a span. So we just slice the doc from min i to max i
            if len(strict_tokens) > 1:
                span2 = doc[strict_tokens[0].i : strict_tokens[-1].i + 1]
                add_span_forms(span2)

    except Exception as e:
        logger.warning(f"dict: spaCy candidate generation failed: {e}")
        
    unique_forms = []
    for f in forms:
        if f not in unique_forms:
            unique_forms.append(f)
            
    return unique_forms

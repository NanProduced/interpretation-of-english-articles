from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.services.dictionary.service import DictionaryService
from scripts.import_tecd3 import (
    build_lookup_forms,
    load_txt_records,
    normalize_query,
    parse_disambiguation_html,
    parse_entry_html,
)


ENTRY_HTML = """
<html><body>
  <div class="eDiv" id="actualize-entry">
    <div class="hg nopos">
      <div class="hgContent">
        <div class="hwgDiv">
          <span class="hwSpan">ac·tu·al·ize</span>
          <span class="hwFollowSpan">
            <span class="prLine"><pr soundfile="root">ˈæktʃʊəlaɪz</pr></span>
          </span>
        </div>
      </div>
    </div>
    <div class="sg">
      <div class="se1">
        <div class="subse1">
          <div class="sgPosDiv"><span class="posg"><span class="pos">TRANSITIVE VERB 及物动词</span></span></div>
          <ol class="se2g">
            <li class="se2"><span class="df">实行(计划等),把…化为行动</span></li>
            <li class="se2"><span class="df">发挥出…的潜力</span></li>
          </ol>
        </div>
        <div class="subse1">
          <div class="sgPosDiv"><span class="posg"><span class="pos">INTRANSITIVE VERB 不及物动词</span></span></div>
          <ol class="se2g">
            <li class="se2"><span class="df">成为现实</span></li>
            <li class="se2"><span class="df">发挥出潜力</span></li>
          </ol>
        </div>
      </div>
    </div>
    <div class="phrase">
      <span class="hwSpan">actualize a plan</span>
      <span class="df">实行计划</span>
    </div>
  </div>
</body></html>
"""


HOMOGRAPH_HTML = """
<html><body>
  <div class="eDiv" id="anth-two">
    <div class="hg nopos">
      <div class="hgContent">
        <div class="hwgDiv">
          <span class="hwSpan"><hw homograph="2">anth-</hw><sup>2</sup></span>
          <span class="hwFollowSpan"><span class="prLine"><pr soundfile="anth">ænθ</pr></span></span>
        </div>
      </div>
    </div>
    <div class="sg">
      <div class="se1">
        <div class="sgPosDiv"><span class="posg"><span class="pos">PREFIX 前缀</span></span></div>
        <ol class="se2g se2gOne">
          <li class="se2">
            <span class="corrSe2FirstLine"><xrg>=<a class="xr" href="entry://anti-">anti-</a></xrg><br/></span>
          </li>
        </ol>
      </div>
    </div>
  </div>
</body></html>
"""


FRAGMENT_HTML = """
<html><body>
  <div class="mdict-fragment-header">
    <div class="mdict-fragment-title">each and all</div>
    <div class="mdict-fragment-parent">主词条：<a class="mdict-parent-link" href="entry://each">each</a></div>
  </div>
  <div class="mdict-fragment-body">
    <div class="phrasediv">
      <ol class="se2g se2gOne">
        <li class="se2">
          <span class="corrSe2FirstLine"><span class="df">人人；各个；全部</span><br/></span>
        </li>
      </ol>
    </div>
  </div>
</body></html>
"""


WBR_HEADWORD_HTML = """
<html><body>
  <div class="eDiv" id="rose-water">
    <div class="hg nopos">
      <div class="hgContent">
        <div class="hwgDiv">
          <span class="hwSpan"><hw>rose <wbr/>water</hw></span>
        </div>
      </div>
    </div>
    <div class="sg">
      <div class="se1">
        <ol class="se2g">
          <li class="se2"><span class="df">玫瑰水</span></li>
          <li class="se2"><span class="df">温和的话语</span></li>
        </ol>
      </div>
    </div>
  </div>
</body></html>
"""


MIXED_SECTION_HTML = """
<html><body>
  <div class="eDiv" id="round-one">
    <div class="hg">
      <div class="hgContent">
        <div class="hwgDiv">
          <span class="hwSpan"><hw homograph="1">round</hw><sup>1</sup></span>
          <span class="hwFollowSpan"><span class="prLine"><pr soundfile="round">raʊnd</pr></span></span>
        </div>
      </div>
    </div>
    <div class="sg">
      <div class="se1">
        <div class="sgPosDiv"><span class="posg"><span class="pos">ADJECTIVE 形容词</span></span></div>
        <ol class="se2g">
          <li class="se2"><span class="df">圆(形)的</span></li>
        </ol>
      </div>
      <div class="se1">
        <div class="subse1">
          <div class="sgPosDiv"><span class="posg"><span class="pos">TRANSITIVE VERB 及物动词</span></span></div>
          <ol class="se2g">
            <li class="se2"><span class="df">使成圆形</span></li>
          </ol>
        </div>
        <div class="subse1">
          <div class="sgPosDiv"><span class="posg"><span class="pos">INTRANSITIVE VERB 不及物动词</span></span></div>
          <ol class="se2g">
            <li class="se2"><span class="df">变圆</span></li>
          </ol>
        </div>
      </div>
    </div>
    <div class="phrase">
      <div class="phrasediv">
        <div class="lDiv"><span class="l">all round</span><br/></div>
        <ol class="se2g se2gOne">
          <li class="se2"><span class="corrSe2FirstLine"><span class="df">见 all</span><br/></span></li>
        </ol>
      </div>
    </div>
  </div>
</body></html>
"""


DISAMB_HTML = """
<html><body>
  <div class="mdict-disamb">
    <div class="mdict-disamb-title">anti</div>
    <div class="mdict-disamb-tip">该检索词命中多个词条，请选择具体入口。</div>
  </div>
  <ul class="mdict-disamb-list">
    <li class="mdict-disamb-item">
      <a class="mdict-target-link" href="entry://anti · n.,a.,prep.">anti</a>
      <div class="mdict-target-meta"><span class="pos">n.,a.,prep.</span></div>
      <div class="mdict-target-preview">1. 反对者,反对分子,持反对论者</div>
    </li>
    <li class="mdict-disamb-item">
      <a class="mdict-target-link" href="entry://anti- · pref.">anti-</a>
      <div class="mdict-target-meta"><span class="pos">pref.</span></div>
      <div class="mdict-target-preview">1. 表示“反”“抗”“阻”</div>
    </li>
  </ul>
</body></html>
"""


def _write_txt(path: Path, contents: str) -> None:
    path.write_text(textwrap.dedent(contents).strip() + "\n", encoding="utf-8")


def test_load_txt_records_reads_html_and_redirects(tmp_path: Path) -> None:
    mdx_file = tmp_path / "sample.mdx.a.txt"
    _write_txt(
        mdx_file,
        """
        anti
        <html><body><div class="mdict-disamb"></div></body></html>
        </>
        anti-
        @@@LINK=anti · n.,a.,prep.
        </>
        """,
    )

    records = load_txt_records(tmp_path)

    assert records["anti"].kind == "html"
    assert records["anti-"].kind == "redirect"
    assert records["anti-"].value == "anti · n.,a.,prep."


def test_load_txt_records_rejects_duplicate_keys(tmp_path: Path) -> None:
    mdx_file = tmp_path / "sample.mdx.a.txt"
    _write_txt(
        mdx_file,
        """
        anti
        <html><body><div class="eDiv"></div></body></html>
        </>
        anti
        @@@LINK=anti · n.,a.,prep.
        </>
        """,
    )

    with pytest.raises(ValueError, match="Duplicate mdict key"):
        load_txt_records(tmp_path)


def test_parse_entry_html_extracts_entry_payload() -> None:
    parsed = parse_entry_html("actualize", ENTRY_HTML)

    assert parsed is not None
    assert parsed.source_entry_key == "actualize"
    assert parsed.entry_kind == "entry"
    assert parsed.display_headword == "actualize"
    assert parsed.base_headword == "actualize"
    assert parsed.homograph_no is None
    assert parsed.phonetic == "ˈæktʃʊəlaɪz"
    assert parsed.primary_pos == "vt."
    assert parsed.meanings_json[0]["part_of_speech"] == "vt."
    assert parsed.meanings_json[1]["part_of_speech"] == "vi."
    assert parsed.phrases_json[0]["phrase"] == "actualize a plan"
    assert parsed.sections_json


def test_parse_entry_html_handles_homograph_labels_and_xrg_meanings() -> None:
    parsed = parse_entry_html("anth- · pref.", HOMOGRAPH_HTML)

    assert parsed is not None
    assert parsed.display_headword == "anth-²"
    assert parsed.base_headword == "anth-"
    assert parsed.homograph_no == 2
    assert parsed.phonetic == "ænθ"
    assert parsed.primary_pos == "pref."
    assert parsed.meanings_json[0]["definitions"][0]["meaning"] == "=anti-"


def test_parse_entry_html_handles_fragment_entries() -> None:
    parsed = parse_entry_html("each and all", FRAGMENT_HTML)

    assert parsed is not None
    assert parsed.entry_kind == "fragment"
    assert parsed.display_headword == "each and all"
    assert parsed.base_headword == "each and all"
    assert parsed.meanings_json[0]["definitions"][0]["meaning"] == "人人；各个；全部"


def test_parse_entry_html_preserves_wbr_spacing_in_headwords() -> None:
    parsed = parse_entry_html("rose water · 1. 玫瑰水", WBR_HEADWORD_HTML)

    assert parsed is not None
    assert parsed.display_headword == "rose water"
    assert parsed.base_headword == "rose water"


def test_parse_entry_html_preserves_superscript_display_and_keeps_all_pos_sections() -> None:
    parsed = parse_entry_html("round¹", MIXED_SECTION_HTML)

    assert parsed is not None
    assert parsed.display_headword == "round¹"
    assert parsed.base_headword == "round"
    assert parsed.homograph_no == 1
    assert [group["part_of_speech"] for group in parsed.meanings_json] == [
        "adj.",
        "vt.",
        "vi.",
    ]
    assert parsed.phrases_json[0]["phrase"] == "all round"
    assert parsed.phrases_json[0]["meaning"] == "见 all"


def test_parse_disambiguation_html_extracts_candidates() -> None:
    parsed = parse_disambiguation_html("anti", DISAMB_HTML)

    assert parsed is not None
    assert parsed.lookup_key == "anti"
    assert parsed.lookup_label == "anti"
    assert parsed.normalized_form == "anti"
    assert len(parsed.candidates) == 2
    assert parsed.candidates[0].target_entry_key == "anti · n.,a.,prep."
    assert parsed.candidates[1].label == "anti-"
    assert parsed.candidates[1].target_pos == "pref."


def test_build_lookup_forms_expands_hyphen_and_apostrophe_variants() -> None:
    forms = build_lookup_forms("world's-best")

    assert "world's-best" in forms
    assert "worlds-best" in forms
    assert "world's best" in forms
    assert "worldsbest" in forms


def test_normalize_query_and_service_normalize_align() -> None:
    service = DictionaryService()

    assert normalize_query(" U.S. ") == "us"
    assert normalize_query("anth- 2") == "anth-2"
    assert service._normalize("“World’s”") == "world's"
    assert service._normalize("(state-owned)") == "state-owned"
    assert service._candidate_queries("landings") == ["landings", "landing"]
    assert service._candidate_queries("bodies") == ["bodies", "body"]

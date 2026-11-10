"""v0.2 공개 전 정리: GFM 이스케이프·빈 표·각주 안 표, 옵션 검증·기록, 메모 경계 사례."""
import json

import pytest
from helpers import FIX, blocks_of, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert
from hwppipe.render_md import render


def _md(tmp_path, inner, **kw):
    convert(make_hwpx(tmp_path, inner), tmp_path / "o", **kw)
    return (tmp_path / "o/document.md").read_text(encoding="utf-8")


def test_gfm_escapes_backslash_before_pipe(tmp_path):
    md = _md(tmp_path, para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("a\\|b"))])), table_format="gfm")
    assert "| a\\\\\\|b |" in md  # 원문 a\|b → a\\\|b (백슬래시와 파이프를 각각 이스케이프)


def test_gfm_empty_table_writes_no_pipe_row(tmp_path):
    md = _md(tmp_path, para("앞") + para_raw(tbl_xml(0, 0, [])), table_format="gfm")
    assert "|" not in md


def test_gfm_table_in_footnote_stays_a_table(tmp_path):
    note = ('<hp:ctrl><hp:footNote><hp:subList>' + para("설명") +
            para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("v"))])) + '</hp:subList></hp:footNote></hp:ctrl>')
    md = _md(tmp_path, para_raw("<hp:t>본문</hp:t>" + note), table_format="gfm")
    assert "[^fn-1]: 설명\n" in md and "\n    | --- |" in md


def test_render_rejects_unknown_table_format():
    with pytest.raises(ValueError):
        render({"blocks": []}, "GFM")


def test_report_records_options_and_schema_version(tmp_path):
    r = convert(FIX / "SimpleTable.hwpx", tmp_path / "o", table_format="gfm")
    assert r["options"] == {"table_format": "gfm", "unframe_layout_tables": False}
    dj = json.loads((tmp_path / "o/document.json").read_text(encoding="utf-8"))
    assert dj["schema_version"] == "1.1"


def _memo(i):
    return (f'<hp:ctrl><hp:fieldBegin type="MEMO"{f" id={chr(34)}{i}{chr(34)}" if i else ""}><hp:subList>'
            + para("메모") + '</hp:subList></hp:fieldBegin></hp:ctrl>')


END = '<hp:ctrl><hp:fieldEnd beginIDRef="1"/></hp:ctrl>'


def test_auto_number_is_part_of_memo_anchor(tmp_path):
    num = '<hp:ctrl><hp:autoNum num="1" numType="TABLE"><hp:autoNumFormat type="DIGIT"/></hp:autoNum></hp:ctrl>'
    _, ctx = blocks_of(tmp_path, para_raw(_memo(1) + "<hp:t>표 </hp:t>" + num + END))
    assert ctx.memos[0]["anchor"] == "표 1"


def test_rolled_back_table_does_not_touch_memo(tmp_path):
    bad = tbl_xml(1, 2, [(0, 0, 1, 1, para_raw("<hp:t>셀글</hp:t>" + END)), (0, 1, 1, 1, para("x"))])
    bad = bad.replace('colAddr="1"', 'colAddr="zz"')
    _, ctx = blocks_of(tmp_path, para_raw(_memo(1) + "<hp:t>앞</hp:t>" + bad + "<hp:t>뒤</hp:t>" + END))
    assert ctx.memos[0]["anchor"] == "앞뒤"


def test_memos_without_id_get_no_anchor(tmp_path):
    _, ctx = blocks_of(tmp_path, para_raw(_memo(None) + "<hp:t>가</hp:t>" + _memo(None) + "<hp:t>나</hp:t>"))
    assert [m["anchor"] for m in ctx.memos] == [None, None]

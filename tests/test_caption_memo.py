"""비교 마일스톤에서 찾은 손실(글상자 캡션, 한글 메모)의 회귀 테스트."""
import json

from helpers import FIX, blocks_of, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert


def _out(tmp_path, src):
    r = convert(src, tmp_path / "o")
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    dj = json.loads((tmp_path / "o/document.json").read_text(encoding="utf-8"))
    return r, md, dj


def _balanced(r):
    return r["counts"]["chars_source"] == r["counts"]["chars_emitted"] + sum(x["chars"] for x in r["losses"])


def test_rect_caption_is_kept(tmp_path):
    r, md, dj = _out(tmp_path, FIX / "SimpleRectangle.hwpx")
    box = next(b for b in dj["blocks"] if b["type"] == "textbox")
    assert box["caption"].startswith("그림") and "그림" in md and "ABC" in md
    assert _balanced(r)


def test_caption_only_shape_is_kept(tmp_path):
    rect = '<hp:rect><hp:caption side="BOTTOM"><hp:subList>' + para("도형 설명") + '</hp:subList></hp:caption></hp:rect>'
    r, md, dj = _out(tmp_path, make_hwpx(tmp_path, para_raw(rect)))
    assert "도형 설명" in md and _balanced(r)


def test_equation_caption_is_output(tmp_path):
    eq = ('<hp:equation><hp:script>x</hp:script><hp:caption side="BOTTOM"><hp:subList>' + para("식 설명") +
          '</hp:subList></hp:caption></hp:equation>')
    r, md, dj = _out(tmp_path, make_hwpx(tmp_path, para_raw(eq)))
    assert dj["blocks"][0]["equations"][0]["caption"] == "식 설명"
    assert "<!-- hwpeq: x -->\n식 설명" in md and r["losses"] == [] and _balanced(r)


def test_caption_auto_number(tmp_path):
    _, md, dj = _out(tmp_path, FIX / "SimpleRectangle.hwpx")
    assert next(b for b in dj["blocks"] if b["type"] == "textbox")["caption"].strip() == "그림 1"


def test_page_auto_number_is_not_text(tmp_path):
    b, _ = blocks_of(tmp_path, para_raw('<hp:t>쪽 </hp:t><hp:ctrl><hp:autoNum num="7" numType="PAGE">'
                                        '<hp:autoNumFormat type="DIGIT"/></hp:autoNum></hp:ctrl>'))
    assert b[0]["text"] == "쪽 "


def test_auto_number_format(tmp_path):
    b, ctx = blocks_of(tmp_path, para_raw('<hp:t>표</hp:t><hp:ctrl><hp:autoNum num="3" numType="TABLE">'
                                          '<hp:autoNumFormat type="ROMAN_CAPITAL" prefixChar="(" suffixChar=")"/>'
                                          '</hp:autoNum></hp:ctrl>'))
    assert b[0]["text"] == "표(III)" and (ctx.chars_source, ctx.chars_emitted) == (1, 1)


MEMO = ('<hp:t>붙은 글</hp:t><hp:ctrl><hp:fieldBegin type="MEMO" id="7"><hp:parameters cnt="3">'
        '<hp:stringParam name="Author">홍길동</hp:stringParam><hp:integerParam name="Number">1</hp:integerParam>'
        '<hp:stringParam name="CreateDateTime">2024-03-14T22:38:25Z</hp:stringParam></hp:parameters>'
        '<hp:subList>' + para("메모 첫 줄") + para("둘째 줄") + '</hp:subList></hp:fieldBegin></hp:ctrl>'
        '<hp:ctrl><hp:fieldEnd beginIDRef="7"/></hp:ctrl>')


def test_memo_is_output(tmp_path):
    r, md, dj = _out(tmp_path, make_hwpx(tmp_path, para_raw(MEMO)))
    m = dj["memos"][0]
    assert (m["author"], m["created"], m["number"], m["text"]) == ("홍길동", "2024-03-14T22:38:25Z", 1,
                                                                   "메모 첫 줄\n둘째 줄")
    assert m["loc"]["para"] == 0
    assert "> [메모 · 홍길동 · 2024-03-14] 메모 첫 줄\n> 둘째 줄" in md
    assert r["losses"] == [] and r["counts"]["memos"] == 1 and _balanced(r)


def test_non_memo_field_with_text_is_still_a_loss(tmp_path):
    f = '<hp:ctrl><hp:fieldBegin type="UNKNOWN"><hp:subList>' + para("필드 글") + '</hp:subList></hp:fieldBegin></hp:ctrl>'
    _, ctx = blocks_of(tmp_path, para_raw("<hp:t>본문</hp:t>" + f))
    assert ctx.losses["fieldBegin"][0]["chars"] == 4


def test_memo_anchor_text(tmp_path):
    inner = ('<hp:t>앞 </hp:t>' + MEMO[MEMO.index("<hp:ctrl>"):MEMO.index("<hp:ctrl><hp:fieldEnd")] +
             '<hp:t>붙은 글</hp:t><hp:ctrl><hp:fieldEnd beginIDRef="7"/></hp:ctrl><hp:t> 뒤</hp:t>')
    r, md, dj = _out(tmp_path, make_hwpx(tmp_path, para_raw(inner)))
    assert dj["memos"][0]["anchor"] == "붙은 글"
    assert "> [메모 · 홍길동 · 2024-03-14] 메모 첫 줄\n> 둘째 줄\n> 붙은 글: 붙은 글" in md
    assert dj["blocks"][0]["text"] == "앞 붙은 글 뒤" and _balanced(r)


def _memo(i, body=None):
    return (f'<hp:ctrl><hp:fieldBegin type="MEMO" id="{i}"><hp:subList>' + (body or para("메모")) +
            '</hp:subList></hp:fieldBegin></hp:ctrl>')


def _end(i):
    return f'<hp:ctrl><hp:fieldEnd beginIDRef="{i}"/></hp:ctrl>'


def test_unended_memo_does_not_swallow_section(tmp_path):
    _, ctx = blocks_of(tmp_path, para_raw(_memo(1) + "<hp:t>붙음</hp:t>") + para("둘째 문단"))
    assert ctx.memos[0]["anchor"] is None
    assert any("fieldEnd" in w for w in ctx.warnings)


def test_unended_memo_inside_memo_is_closed(tmp_path):
    outer = _memo(1, para_raw("<hp:t>바깥</hp:t>" + _memo(2)))
    _, ctx = blocks_of(tmp_path, para_raw(outer + "<hp:t>X</hp:t>" + _end(1) + "<hp:t>본문뒤</hp:t>"))
    anchors = {m["text"]: m["anchor"] for m in ctx.memos}
    assert anchors == {"메모": None, "바깥": "X"}


def test_memo_anchor_skips_notes_and_keeps_paragraph_breaks(tmp_path):
    note = '<hp:ctrl><hp:footNote><hp:subList>' + para("각주내용") + '</hp:subList></hp:footNote></hp:ctrl>'
    _, ctx = blocks_of(tmp_path, para_raw(_memo(1) + "<hp:t>첫문단</hp:t>" + note) +
                       para_raw("<hp:t>둘째</hp:t>" + _end(1)))
    assert ctx.memos[0]["anchor"] == "첫문단\n둘째"


def test_memo_anchor_across_table_keeps_cell_breaks(tmp_path):
    t = tbl_xml(1, 2, [(0, 0, 1, 1, para("셀A")), (0, 1, 1, 1, para("셀B"))])
    _, ctx = blocks_of(tmp_path, para_raw(_memo(1) + "<hp:t>앞</hp:t>" + t + "<hp:t>뒤</hp:t>" + _end(1)))
    assert ctx.memos[0]["anchor"] == "앞\n셀A\n셀B\n뒤"

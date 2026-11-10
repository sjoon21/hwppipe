"""PyPI 등록 전 보강: 수식·머리말 id, 메모 연결 대상, 청킹 예제."""
from helpers import make_hwpx, para, para_raw

from hwppipe import parse, to_graph


def _edges(g, t):
    return {(e["source"], e["target"]) for e in g["edges"] if e["type"] == t}


def test_equation_ids_match_graph(tmp_path):
    eq = '<hp:equation><hp:script>x</hp:script></hp:equation>'
    doc = parse(make_hwpx(tmp_path, para_raw("<hp:t>식</hp:t>" + eq + eq)))
    ids = [e["id"] for e in doc["blocks"][0]["equations"]]
    assert ids == ["eq-001", "eq-002"]
    assert {(doc["blocks"][0]["id"], i) for i in ids} <= _edges(to_graph(doc), "HAS_EQUATION")


def _hf(kind, text, memo=""):
    return (f'<hp:ctrl><hp:{kind} applyPageType="BOTH"><hp:subList>' + para_raw(f"<hp:t>{text}</hp:t>" + memo) +
            f'</hp:subList></hp:{kind}></hp:ctrl>')


MEMO = ('<hp:ctrl><hp:fieldBegin type="MEMO" id="1"><hp:subList>' + para("메모") +
        '</hp:subList></hp:fieldBegin></hp:ctrl><hp:ctrl><hp:fieldEnd beginIDRef="1"/></hp:ctrl>')


def test_header_footer_ids_and_memo_target(tmp_path):
    doc = parse(make_hwpx(tmp_path, para_raw(_hf("header", "첫 머리말") + _hf("header", "둘째 머리말", MEMO) +
                                             _hf("footer", "꼬리말") + "<hp:t>본문</hp:t>")))
    assert [h["id"] for h in doc["headers_footers"]] == ["header-001", "header-002", "footer-001"]
    assert all(b["loc"]["in"] == h["id"] for h in doc["headers_footers"] for b in h["blocks"])
    g = to_graph(doc)
    second = doc["headers_footers"][1]["blocks"][0]["id"]
    assert ("memo-001", second) in _edges(g, "ANNOTATES")
    assert ("sec-0", "header-002") in _edges(g, "HAS_HEADER")


def test_memo_in_caption_points_to_captioned_object(tmp_path):
    tbl = ('<hp:tbl rowCnt="1" colCnt="1"><hp:caption side="BOTTOM"><hp:subList>' +
           para_raw("<hp:t>표 설명</hp:t>" + MEMO) + '</hp:subList></hp:caption><hp:tr><hp:tc><hp:subList>' +
           para("셀") + '</hp:subList><hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
           '</hp:tc></hp:tr></hp:tbl>')
    doc = parse(make_hwpx(tmp_path, para_raw(tbl)))
    assert ("memo-001", "tbl-001") in _edges(to_graph(doc), "ANNOTATES")


def test_markdown_does_not_turn_indented_text_into_code_or_headings(tmp_path):
    import json
    from hwppipe import convert
    convert(make_hwpx(tmp_path, para("    ■ 3월 일정") + para("\t⇨ 좌석") + para("# 아님")), tmp_path / "o")
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    assert "\n■ 3월 일정" in "\n" + md and "\n⇨ 좌석" in md and "\n\\# 아님" in md
    dj = json.loads((tmp_path / "o/document.json").read_text(encoding="utf-8"))
    assert dj["blocks"][0]["text"] == "    ■ 3월 일정"  # 구조 데이터는 원문 그대로


def _rel_hpf():
    return ('<?xml version="1.0" encoding="UTF-8"?><opf:package xmlns:opf="http://www.idpf.org/2007/opf/">'
            '<opf:manifest><opf:item id="header" href="header.xml" media-type="application/xml"/>'
            '<opf:item id="section0" href="section0.xml" media-type="application/xml"/></opf:manifest>'
            '<opf:spine><opf:itemref idref="header"/><opf:itemref idref="section0"/></opf:spine></opf:package>').encode()


def test_manifest_hrefs_relative_to_contents(tmp_path):
    doc, rep = parse(make_hwpx(tmp_path, para("본문 글"), files={"Contents/content.hpf": _rel_hpf()}), with_report=True)
    assert doc["blocks"][0]["text"] == "본문 글" and rep["status"] == "ok"


def test_document_without_sections_is_partial(tmp_path):
    hpf = _rel_hpf().replace(b'href="section0.xml"', b'href="nothing.xml"')
    doc, rep = parse(make_hwpx(tmp_path, para("x"), files={"Contents/content.hpf": hpf}), with_report=True)
    assert rep["status"] == "partial" and any("구역" in w for w in rep["warnings"])


def test_control_characters_do_not_drop_a_section(tmp_path):
    doc, rep = parse(make_hwpx(tmp_path, para_raw("<hp:t>앞\x01뒤</hp:t>")), with_report=True)
    assert doc["blocks"][0]["text"] == "앞뒤" and rep["status"] == "ok"


def test_empty_picture_frame_is_not_a_loss(tmp_path):
    pic = '<hp:pic><hc:img binaryItemIDRef=""/></hp:pic>'
    doc, rep = parse(make_hwpx(tmp_path, para_raw("<hp:t>본문</hp:t>" + pic)), with_report=True)
    assert rep["losses"] == [] and [b["type"] for b in doc["blocks"]] == ["paragraph"]


def _text_and_losses(src):
    from hwppipe.writer import _iter
    doc, rep = parse(src, with_report=True)
    text = "\n".join(b.get("text", "") for top in doc["blocks"] for b in _iter([top]))
    return text, {x["kind"] for x in rep["losses"]}, rep


def test_compose_and_dutmal_text_is_kept():
    from helpers import FIX
    text, losses, rep = _text_and_losses(FIX / "SimpleCompose.hwpx")
    assert "12" in text and "AO" in text and "compose" not in losses
    text, losses, _ = _text_and_losses(FIX / "SimpleDutmal.hwpx")
    assert "테스트_본말(테스트_닷말)" in text and "dutmal" not in losses


def test_form_controls_keep_label_and_state():
    from helpers import FIX
    text, losses, _ = _text_and_losses(FIX / "SimpleButtons.hwpx")
    assert "☐ 선택 상자1" in text and "○ 라디오 단추1" in text
    assert not losses & {"btn", "checkBtn", "radioBtn"}
    text, losses, _ = _text_and_losses(FIX / "SimpleEdit.hwpx")  # passwordChar="X"인 암호 입력란
    assert "1234" not in text and "password_field" in losses and "edit" not in losses


def test_checked_box_and_run_level_line_break(tmp_path):
    x = ('<hp:checkBtn caption="동의" value="CHECKED"/><hp:radioBtn caption="예" value="CHECKED"/>'
         '<hp:t>가</hp:t><hp:lineBreak/><hp:t>나</hp:t>')
    doc, rep = parse(make_hwpx(tmp_path, para_raw(x)), with_report=True)
    assert doc["blocks"][0]["text"] == "☑ 동의◉ 예가\n나" and rep["losses"] == []


def test_vertical_tab_becomes_line_break_and_is_reported(tmp_path):
    doc, rep = parse(make_hwpx(tmp_path, para_raw("<hp:t>가\x0b나\x01다</hp:t>")), with_report=True)
    assert doc["blocks"][0]["text"] == "가\n나다"
    assert any("제어 문자" in w for w in rep["warnings"])


def test_failed_repair_keeps_original_error():
    import pytest
    from lxml import etree
    from hwppipe.xml import parse as xml_parse
    with pytest.raises(etree.XMLSyntaxError, match="PCDATA invalid Char"):
        xml_parse(b"<a>\x01</a><b>")  # 제어 문자를 지워도 다른 오류가 남으면 원래 오류를 알린다
    with pytest.raises(etree.XMLSyntaxError):
        xml_parse('<?xml version="1.0" encoding="UTF-16"?><a>\x01</a>'.encode("utf-16"))


def test_blank_attribute_text_is_not_counted_as_emitted(tmp_path):
    doc, rep = parse(make_hwpx(tmp_path, para_raw("<hp:edit><hp:text>   </hp:text></hp:edit>") + para("다음")),
                     with_report=True)
    assert rep["counts"]["chars_emitted"] == 2


def test_quote_bodies_and_setext_lines_are_safe_markdown(tmp_path):
    from hwppipe.render_md import render
    md = render({"blocks": [{"type": "paragraph", "text": "제목처럼\n===", "loc": {}},
                            {"type": "paragraph", "text": "---", "loc": {}}],
                 "memos": [{"id": "memo-001", "text": "첫 줄\n      들여 쓴 줄", "loc": {}}]})
    assert "제목처럼\n\\===" in md and "\n\\---\n" in md and "> 들여 쓴 줄" in md


def test_relative_href_prefers_contents_folder(tmp_path):
    hpf = _rel_hpf()
    src = make_hwpx(tmp_path, para("본문 글"), files={"Contents/content.hpf": hpf, "section0.xml": b"<x/>"})
    assert parse(src)["blocks"][0]["text"] == "본문 글"


def test_memo_in_empty_cell_paragraph_points_to_cell(tmp_path):
    from helpers import tbl_xml
    t = tbl_xml(1, 1, [(0, 0, 1, 1, para_raw(MEMO))])
    doc = parse(make_hwpx(tmp_path, para_raw(t)))
    assert ("memo-001", "tbl-001[0,0]") in _edges(to_graph(doc), "ANNOTATES")


def test_password_edit_value_is_not_output(tmp_path):
    x = ('<hp:edit passwordChar=""><hp:text>보통 값</hp:text></hp:edit>'
         '<hp:edit passwordChar="*"><hp:text>비밀1</hp:text></hp:edit>'
         '<hp:edit><hp:text>비밀2</hp:text></hp:edit>')  # 속성이 없으면 스키마 기본값 "*"
    doc, rep = parse(make_hwpx(tmp_path, para_raw(x)), with_report=True)
    assert "보통 값" in doc["blocks"][0]["text"] and "비밀" not in doc["blocks"][0]["text"]
    loss = next(x for x in rep["losses"] if x["kind"] == "password_field")
    assert (loss["count"], loss["chars"]) == (2, 6)
    c = rep["counts"]
    assert c["chars_source"] == c["chars_emitted"] + sum(x["chars"] for x in rep["losses"])


def test_picture_that_lost_its_image_is_still_a_loss(tmp_path):
    pic = ('<hp:pic><hp:shapeComment>그림입니다.\n원본 그림의 이름: 사진.png</hp:shapeComment>'
           '<hc:img binaryItemIDRef=""/></hp:pic>')
    doc, rep = parse(make_hwpx(tmp_path, para_raw("<hp:t>본문</hp:t>" + pic)), with_report=True)
    assert any(x["kind"] == "missing_binary" for x in rep["losses"])

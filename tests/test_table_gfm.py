"""--table-format gfm: HTML을 쓰지 않는 Markdown 표."""
from helpers import FIX, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert
from hwppipe.cli import main


def _md(tmp_path, src):
    convert(src, tmp_path / "o", table_format="gfm")
    return (tmp_path / "o/document.md").read_text(encoding="utf-8")


def test_merged_cells_get_annotations(tmp_path):
    md = _md(tmp_path, FIX / "SimpleTable.hwpx")
    assert "<table" not in md
    assert md.count("[병합 2×2]") == 1 and md.count("[병합 1×2]") == 1
    lines = [x for x in md.splitlines() if x.startswith("|")]
    assert lines[1] == "| --- | --- | --- |" and len(lines) == 4  # 머리 행 + 구분선 + 2행


def test_nested_table_is_emitted_after_parent(tmp_path):
    inner = tbl_xml(1, 1, [(0, 0, 1, 1, para("속"))])
    t = tbl_xml(1, 2, [(0, 0, 1, 1, para("바깥")), (0, 1, 1, 1, para_raw(inner))])
    md = _md(tmp_path, make_hwpx(tmp_path, para_raw(t)))
    assert "| 바깥 | [표 tbl-002] |" in md
    assert md.index("<!-- table:tbl-002 (tbl-001 안) -->") > md.index("| 바깥 |")
    assert "| 속 |" in md


def test_pipe_and_newline_in_cell(tmp_path):
    t = tbl_xml(1, 1, [(0, 0, 1, 1, para("a|b") + para("둘째"))])
    md = _md(tmp_path, make_hwpx(tmp_path, para_raw(t)))
    assert "| a\\|b 둘째 |" in md


def test_cli_option(tmp_path):
    assert main([str(FIX / "SimpleTable.hwpx"), "-o", str(tmp_path / "o"), "--table-format", "gfm"]) == 0
    md = (tmp_path / "o/SimpleTable/document.md").read_text(encoding="utf-8")
    assert "<table" not in md and "[병합 2×2]" in md


def test_default_is_html(tmp_path):
    convert(FIX / "SimpleTable.hwpx", tmp_path / "o")
    assert "<table>" in (tmp_path / "o/document.md").read_text(encoding="utf-8")


def test_bottom_caption_is_outside_table(tmp_path):
    t = tbl_xml(1, 2, [(0, 0, 1, 1, para("a")), (0, 1, 1, 1, para("b"))], caption="표 설명", side="BOTTOM")
    md = _md(tmp_path, make_hwpx(tmp_path, para_raw(t)))
    assert "| --- | --- |\n\n표 설명" in md  # 빈 줄이 없으면 GFM이 캡션을 표의 행으로 읽는다


def test_parent_caption_comes_before_nested_tables(tmp_path):
    inner = tbl_xml(1, 1, [(0, 0, 1, 1, para("속"))])
    t = tbl_xml(1, 1, [(0, 0, 1, 1, para_raw(inner))], caption="부모 캡션", side="BOTTOM")
    md = _md(tmp_path, make_hwpx(tmp_path, para_raw(t)))
    assert "\n\n부모 캡션\n\n" in md and md.index("부모 캡션") < md.index("<!-- table:tbl-002")


def test_equation_caption_in_cell(tmp_path):
    eq = ('<hp:equation><hp:script>x</hp:script><hp:caption side="BOTTOM"><hp:subList>' + para("식 설명") +
          '</hp:subList></hp:caption></hp:equation>')
    src = make_hwpx(tmp_path, para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para_raw(eq))])))
    assert "식 설명" in _md(tmp_path, src)
    convert(src, tmp_path / "h")
    assert "식 설명" in (tmp_path / "h/document.md").read_text(encoding="utf-8")


def test_equation_caption_in_heading_and_list_item():
    from hwppipe.render_md import render
    eqs = [{"script": "x", "latex": "x", "caption": "식 설명"}]
    for b in ({"type": "heading", "level": 1, "text": "제목 $x$", "equations": eqs},
              {"type": "list_item", "level": 1, "prefix": "-", "text": "항목 $x$", "equations": eqs}):
        assert "식 설명" in render({"blocks": [b]})

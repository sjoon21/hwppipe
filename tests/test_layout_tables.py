"""테두리가 보이지 않는 틀 표: document.json에 layout 표시, --unframe-layout-tables면 Markdown에서 문단으로 푼다."""
import json

from helpers import FIX, HEADER_XML, all_blocks, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert
from hwppipe.cli import main
from hwppipe.header import parse_header

# SimpleTable 머리말 정의: borderFill 1·2는 네 변이 모두 NONE, 3은 SOLID
CELLS = [(0, 0, 1, 1, para("왼쪽")), (0, 1, 1, 1, para("오른쪽"))]


def _doc(tmp_path, border_fill, **kw):
    tmp_path.mkdir(exist_ok=True)
    src = make_hwpx(tmp_path, para("앞") + para_raw(tbl_xml(1, 2, CELLS, border_fill=border_fill)) + para("뒤"))
    convert(src, tmp_path / "o", **kw)
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    dj = json.loads((tmp_path / "o/document.json").read_text(encoding="utf-8"))
    return md, next(b for b in dj["blocks"] if b["type"] == "table")


def test_invisible_border_fills_parsed():
    assert parse_header(HEADER_XML).invisible_border_fills == {"1", "2"}


def test_layout_flag(tmp_path):
    assert _doc(tmp_path / "a", "1")[1]["layout"] is True
    assert _doc(tmp_path / "b", "3")[1]["layout"] is False
    assert _doc(tmp_path / "c", None)[1]["layout"] is False  # 테두리 정보가 없으면 판정하지 않는다


def test_real_table_fixture_is_not_layout():
    assert next(b for b in all_blocks(FIX / "SimpleTable.hwpx") if b["type"] == "table")["layout"] is False


def test_default_keeps_layout_table(tmp_path):
    md, _ = _doc(tmp_path, "1")
    assert "<table>" in md


def test_unframe_option(tmp_path):
    md, table = _doc(tmp_path, "1", unframe_layout_tables=True)
    assert "<table>" not in md and "table:tbl-001" not in md
    assert md.index("앞") < md.index("왼쪽") < md.index("오른쪽") < md.index("뒤")
    assert table["cells"]  # document.json은 표 구조를 그대로 둔다


def test_unframe_keeps_visible_tables(tmp_path):
    md, _ = _doc(tmp_path, "3", unframe_layout_tables=True)
    assert "<table>" in md


def test_cli_option(tmp_path):
    src = make_hwpx(tmp_path, para_raw(tbl_xml(1, 2, CELLS, border_fill="1")))
    assert main([str(src), "-o", str(tmp_path / "o"), "--unframe-layout-tables"]) == 0
    assert "<table>" not in (tmp_path / "o/t/document.md").read_text(encoding="utf-8")


def test_unframe_keeps_caption(tmp_path):
    t = tbl_xml(1, 2, CELLS, caption="틀 캡션", side="BOTTOM", border_fill="1")
    convert(make_hwpx(tmp_path, para_raw(t)), tmp_path / "o", unframe_layout_tables=True)
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    assert md.index("왼쪽") < md.index("오른쪽") < md.index("틀 캡션")

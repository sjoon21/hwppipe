"""v0.1 리뷰에서 미룬 Minor 항목의 회귀 테스트."""
import json
import shutil

from helpers import FIX, blocks_of, flat_text, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert
from hwppipe.cli import main


def lost_chars(ctx):
    return sum(x["chars"] for v in ctx.losses.values() for x in v)


def test_unhandled_ctrl_child_with_text_is_a_loss(tmp_path):
    b, ctx = blocks_of(tmp_path, para_raw('<hp:t>본문</hp:t><hp:ctrl><hp:memo><hp:subList>' + para("메모 내용") +
                                          '</hp:subList></hp:memo><hp:pageNum/></hp:ctrl>'))
    assert "memo" in ctx.losses and "pageNum" not in ctx.losses
    assert ctx.chars_source == ctx.chars_emitted + lost_chars(ctx)


def test_document_named_report_json_does_not_break_summary(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copy(FIX / "SimpleTable.hwpx", src / "report.json.hwpx")
    assert main([str(src), "-o", str(tmp_path / "out")]) == 0
    s = json.loads((tmp_path / "out/report.json").read_text(encoding="utf-8"))
    assert s["documents"][0]["output"] == "report.json~2"


def test_textart_text_is_kept():
    from helpers import all_blocks
    b = all_blocks(FIX / "SimpleTextArt.hwpx")
    assert "hwpx 라이브러리 테스트 입니다.\nneolord" in flat_text(b)


def test_cell_figure_alt_and_nested_caption(tmp_path):
    pic = '<hp:pic><hc:img binaryItemIDRef="image1"/><hp:caption side="BOTTOM"><hp:subList>' + \
          para("그림 설명") + '</hp:subList></hp:caption></hp:pic>'
    inner = tbl_xml(1, 1, [(0, 0, 1, 1, para("속"))], caption="속 표 제목")
    t = tbl_xml(1, 2, [(0, 0, 1, 1, para_raw(pic)), (0, 1, 1, 1, para_raw(inner))])
    convert(make_hwpx(tmp_path, para_raw(t), bins={"image1.png": b"\x89PNG"}), tmp_path / "o")
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    assert 'alt="fig-001: 그림 설명"' in md and "속 표 제목" in md


def test_objects_inside_deleted_range_are_dropped(tmp_path):
    inner = para_raw('<hp:t>남김<hp:deleteBegin Id="1"/></hp:t>'
                     '<hp:pic><hc:img binaryItemIDRef="image1"/></hp:pic>'
                     '<hp:t><hp:deleteEnd Id="1"/>끝</hp:t>')
    b, _ = blocks_of(tmp_path, inner)
    assert [x["type"] for x in b] == ["paragraph"] and b[0]["text"] == "남김끝"


def test_blank_paragraph_not_counted_as_emitted(tmp_path):
    _, ctx = blocks_of(tmp_path, para("   ") + para("글"))
    assert (ctx.chars_source, ctx.chars_emitted) == (1, 1)

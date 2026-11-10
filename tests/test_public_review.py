"""공개 전 최종 리뷰에서 나온 문제의 회귀 테스트."""
import json
import shutil
import time

import pytest
from helpers import FIX, assert_heading_chain, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert, parse, to_graph
from hwppipe.cli import main
from hwppipe.headings import set_heading_paths
from hwppipe.writer import _safe_name


def _h(i, level, text, section=0):
    return {"type": "heading", "id": f"h-{i}", "level": level, "text": text, "loc": {"section": section, "para": i}}


def _p(i, section=0):
    return {"type": "paragraph", "id": f"p-{i}", "text": "본문", "loc": {"section": section, "para": i}}


def test_heading_path_with_skipped_levels():
    blocks = [_h(1, 1, "A"), _h(2, 3, "B"), _h(3, 3, "C"), _p(4)]
    set_heading_paths(blocks)
    assert [b["heading_path"] for b in blocks] == [["A"], ["A", "B"], ["A", "C"], ["A", "C"]]


def test_graph_hierarchy_continues_across_sections():
    blocks = [_h(1, 1, "A"), _p(2, section=1)]
    set_heading_paths(blocks)
    g = to_graph({"source": {}, "metadata": {}, "blocks": blocks})
    contains = {(e["source"], e["target"]) for e in g["edges"] if e["type"] == "CONTAINS"}
    assert ("h-1", "p-2") in contains and blocks[1]["heading_path"] == ["A"]


def test_memo_in_section_without_blocks_points_to_section():
    g = to_graph({"source": {}, "metadata": {}, "blocks": [],
                  "memos": [{"id": "memo-001", "text": "m", "loc": {"section": 0, "para": 0}}]})
    assert {"source": "memo-001", "target": "sec-0", "type": "ANNOTATES"} in g["edges"]


def test_graph_nodes_have_flat_loc_properties():
    g = to_graph({"source": {}, "metadata": {}, "blocks": [
        {"type": "paragraph", "id": "p-1", "text": "x", "loc": {"section": 0, "in": "tbl-001[0,1]", "para": 2}}]})
    p = next(n for n in g["nodes"] if n["id"] == "p-1")
    assert "loc" not in p and (p["loc_section"], p["loc_in"], p["loc_para"]) == (0, "tbl-001[0,1]", 2)
    assert all(not isinstance(v, dict) for n in g["nodes"] for v in n.values())  # 그래프 DB 속성으로 넣을 수 있다


@pytest.mark.parametrize("rows,cols,rs,cs", [(100000, 100000, 1, 1), (1, 1, 1000000, 1000)])
def test_huge_declared_table_is_bounded(tmp_path, rows, cols, rs, cs):
    src = make_hwpx(tmp_path, para("앞") + para_raw(tbl_xml(rows, cols, [(0, 0, rs, cs, para("x"))])))
    t = time.time()
    r = convert(src, tmp_path / "o")
    assert time.time() - t < 5 and len(r["warnings"]) < 20
    assert any(x["kind"] == "broken_tbl" for x in r["losses"])
    assert "앞" in (tmp_path / "o/document.md").read_text(encoding="utf-8")


def test_grid_warnings_are_capped(tmp_path):
    src = make_hwpx(tmp_path, para_raw(tbl_xml(30, 30, [(0, 0, 1, 1, para("x"))])))
    r = convert(src, tmp_path / "o")
    assert len(r["warnings"]) <= 6 and any("외" in w for w in r["warnings"])


def test_tree_refuses_to_overwrite_foreign_report(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    shutil.copy(FIX / "SimpleTable.hwpx", src / "a.hwpx")
    out = tmp_path / "out"
    out.mkdir()
    (out / "report.json").write_text("USER DATA", encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(src), "-o", str(out)])
    assert (out / "report.json").read_text(encoding="utf-8") == "USER DATA"
    main([str(src), "-o", str(tmp_path / "out2")])
    assert main([str(src), "-o", str(tmp_path / "out2")]) == 0  # 자기 요약 파일은 다시 써도 된다


def test_parse_can_return_report(tmp_path):
    src = make_hwpx(tmp_path, para("본문"), files={"Contents/header.xml": None})
    doc, report = parse(src, with_report=True)
    assert doc["blocks"][0]["text"] == "본문" and report["status"] == "partial"


def test_skip_removes_stale_output(tmp_path):
    src = tmp_path / "a.hwpx"
    shutil.copy(FIX / "SimpleTable.hwpx", src)
    convert(src, tmp_path / "o")
    src.write_bytes(b"\xD0\xCF\x11\xE0" + b"\0" * 100)
    r = convert(src, tmp_path / "o")
    assert r["status"] == "skipped" and r["options"]["table_format"] == "html"
    assert not (tmp_path / "o").exists()


def test_header_and_footer_ids_count_separately(tmp_path):
    g = to_graph({"source": {}, "metadata": {}, "blocks": [], "headers_footers": [
        {"kind": "header", "apply": "BOTH", "section": 0, "blocks": []},
        {"kind": "footer", "apply": "BOTH", "section": 0, "blocks": []}]})
    assert {n["id"] for n in g["nodes"]} >= {"header-001", "footer-001"}


def test_textart_has_caption_keys(tmp_path):
    doc = parse(make_hwpx(tmp_path, para_raw('<hp:textart text="글맵시"/>')))
    box = doc["blocks"][0]
    assert box["type"] == "textbox" and box["caption"] is None and box["caption_side"] is None


@pytest.mark.parametrize("href", ["BinData/a:b.png", "BinData/CON.png", "BinData/lpt1"])
def test_windows_unsafe_figure_names_are_replaced(href):
    name = _safe_name("image1", href, set())
    assert ":" not in name and name.split(".")[0].upper() not in ("CON", "LPT1")


def test_graph_heading_chain_matches_heading_path():
    doc = parse(FIX / "ParaHead.hwpx") if (FIX / "ParaHead.hwpx").exists() else parse(FIX / "SimpleTable.hwpx")
    assert_heading_chain(doc)


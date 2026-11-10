from helpers import FIX, make_hwpx, para, para_raw, tbl_xml, only_table, flat_text, all_blocks
from hwppipe.table import check_grid

def only_table_of(tmp_path, inner): return only_table(all_blocks(make_hwpx(tmp_path, inner)))
def text(cell): return flat_text(cell["blocks"])

def test_simple_table_merged_cells():
    t = only_table(FIX / "SimpleTable.hwpx")
    assert (t["rows"], t["cols"]) == (3, 3)
    cells = {(c["row"], c["col"]): (c["rowspan"], c["colspan"], text(c)) for c in t["cells"]}
    assert cells == {(0,0):(2,2,"1"), (0,2):(1,1,"2"), (1,2):(1,1,"3"),
                     (2,0):(1,1,"5"), (2,1):(1,2,"4")}
    assert check_grid(t) == []

def test_cells_sorted_row_major():
    assert [(c["row"], c["col"]) for c in only_table(FIX / "SimpleTable.hwpx")["cells"]] == \
           [(0,0),(0,2),(1,2),(2,0),(2,1)]

def test_nested_table_inside_cell(tmp_path):
    # 바깥 1x1 표의 셀 안에 2x1 표
    inner_tbl = tbl_xml(rows=2, cols=1, cells=[(0, 0, 1, 1, para("a")), (1, 0, 1, 1, para("b"))])
    t = only_table_of(tmp_path, para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para_raw(inner_tbl))])))
    nested = t["cells"][0]["blocks"][-1]
    assert nested["type"] == "table" and nested["loc"]["in"] == f'{t["id"]}[0,0]'

def test_check_grid_detects_overlap():
    bad = {"rows": 1, "cols": 2, "cells": [{"row":0,"col":0,"rowspan":1,"colspan":2}, {"row":0,"col":1,"rowspan":1,"colspan":1}]}
    assert check_grid(bad)

def test_table_caption(tmp_path):
    t = only_table_of(tmp_path, para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("x"))], caption="【표 제목】", side="TOP")))
    assert (t["caption"], t["caption_side"]) == ("【표 제목】", "TOP")

def test_header_cell_flag(tmp_path):
    t = only_table_of(tmp_path, para_raw(tbl_xml(2, 1, [(0, 0, 1, 1, para("h")), (1, 0, 1, 1, para("v"))],
                                                header_cells={(0, 0)})))
    assert [c["header"] for c in t["cells"]] == [True, False]

def test_table_not_followed_by_empty_paragraph(tmp_path):
    b = all_blocks(make_hwpx(tmp_path, para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("x"))]))))
    assert [x["type"] for x in b] == ["table"]

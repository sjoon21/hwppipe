from helpers import FIX, make_hwpx, read, para, para_raw, tbl_xml, assigned

def test_parahead_outline_and_numbers():
    b = assigned(FIX / "ParaHead.hwpx")
    h = [(x["prefix"], x["text"], x["level"]) for x in b if x["type"] == "heading"]
    assert h == [("1.","개요1",1), ("가.","개요1-1",2), ("나.","개요1-2",2), ("다.","개요1-3",2),
                 ("2.","개요2",1), ("가.","개요2-1",2), ("1)","개요2-1-1",3)]
    assert all(x["heading_source"] == "outline" for x in b if x["type"] == "heading")
    li = {x["text"]: (x["prefix"], x["level"]) for x in b if x["type"] == "list_item"}
    assert li["번호3-1"] == ("3.1.", 2) and li["글머리1-1"] == ("-", 1)

def test_heading_path():
    b = assigned(FIX / "ParaHead.hwpx")
    x = next(x for x in b if x["text"] == "개요2-1-1")
    assert x["heading_path"] == ["2. 개요2", "가. 개요2-1", "1) 개요2-1-1"]

def test_numbering_inside_cells_kept(tmp_path):
    hdr = read(FIX / "ParaHead.hwpx", "Contents/header.xml")
    cell = para("셀 번호", para_pr="24") + para("셀 개요", para_pr="19")
    p = make_hwpx(tmp_path, para("개요1", para_pr="19") + para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, cell)])),
                  header_xml=hdr)
    b = assigned(p)
    t = next(x for x in b if x["type"] == "table")
    cb = t["cells"][0]["blocks"]
    assert [(x["type"], x["prefix"]) for x in cb] == [("list_item", "1."), ("list_item", "2.")]
    assert t["heading_path"] == ["1. 개요1"]

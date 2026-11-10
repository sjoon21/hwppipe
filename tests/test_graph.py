"""graph.json: 온톨로지·그래프 DB 적재용 노드·엣지 출력과 parse() 메모리 API."""
import json
from collections import Counter

import pytest
from helpers import FIX, make_hwpx, para, para_raw

from hwppipe import convert, parse, to_graph, to_markdown
from hwppipe.writer import _iter

FIXTURES = sorted(FIX.glob("*.hwpx"))


def _edges(g, type_):
    return {(e["source"], e["target"]) for e in g["edges"] if e["type"] == type_}


def test_graph_file_is_written(tmp_path):
    convert(FIX / "SimpleTable.hwpx", tmp_path / "o")
    g = json.loads((tmp_path / "o/graph.json").read_text(encoding="utf-8"))
    types = Counter(n["type"] for n in g["nodes"])
    assert types["Document"] == 1 and types["Section"] == 1 and types["Table"] == 1 and types["Cell"] == 5
    assert ("tbl-001", "tbl-001[0,0]") in _edges(g, "HAS_CELL")
    cell_para = next(n for n in g["nodes"] if n["type"] == "Paragraph" and n["text"] == "1")
    assert ("tbl-001[0,0]", cell_para["id"]) in _edges(g, "CONTAINS")
    assert ("sec-0", "tbl-001") in _edges(g, "CONTAINS") and ("doc", "sec-0") in _edges(g, "HAS_SECTION")


def test_heading_hierarchy_and_reading_order():
    blocks = [{"type": "heading", "id": "h-001", "level": 1, "text": "가", "loc": {"section": 0, "para": 0}},
              {"type": "paragraph", "id": "p-001", "text": "본문", "loc": {"section": 0, "para": 1}},
              {"type": "heading", "id": "h-002", "level": 2, "text": "나", "loc": {"section": 0, "para": 2}},
              {"type": "paragraph", "id": "p-002", "text": "본문2", "loc": {"section": 0, "para": 3}},
              {"type": "heading", "id": "h-003", "level": 1, "text": "다", "loc": {"section": 0, "para": 4}}]
    g = to_graph({"source": {"name": "x.hwpx"}, "metadata": {}, "blocks": blocks})
    assert _edges(g, "CONTAINS") == {("sec-0", "h-001"), ("h-001", "p-001"), ("h-001", "h-002"),
                                     ("h-002", "p-002"), ("sec-0", "h-003")}
    assert _edges(g, "NEXT") == {("h-001", "p-001"), ("p-001", "h-002"), ("h-002", "p-002"), ("p-002", "h-003")}


def test_footnote_reference_and_memo_annotation(tmp_path):
    note = '<hp:ctrl><hp:footNote><hp:subList>' + para("각주 글") + '</hp:subList></hp:footNote></hp:ctrl>'
    memo = ('<hp:ctrl><hp:fieldBegin type="MEMO" id="1"><hp:subList>' + para("메모 글") +
            '</hp:subList></hp:fieldBegin></hp:ctrl>')
    doc = parse(make_hwpx(tmp_path, para_raw("<hp:t>본문</hp:t>" + note + memo + "<hp:t>붙음</hp:t>"
                                             '<hp:ctrl><hp:fieldEnd beginIDRef="1"/></hp:ctrl>')))
    g = to_graph(doc)
    pid = doc["blocks"][0]["id"]
    assert (pid, "fn-1") in _edges(g, "REFERS_TO")
    assert ("memo-001", pid) in _edges(g, "ANNOTATES")
    memo_node = next(n for n in g["nodes"] if n["id"] == "memo-001")
    assert (memo_node["type"], memo_node["text"], memo_node["anchor"]) == ("Memo", "메모 글", "붙음")
    fn_para = next(n for n in g["nodes"] if n.get("text") == "각주 글")
    assert ("fn-1", fn_para["id"]) in _edges(g, "CONTAINS") and ("doc", "fn-1") in _edges(g, "HAS_NOTE")


@pytest.mark.parametrize("src", FIXTURES, ids=lambda p: p.name)
def test_graph_is_well_formed(src):
    doc = parse(src)
    ids = [b["id"] for top in doc["blocks"] + doc["notes"] + doc["headers_footers"]
           for b in _iter([top]) if b.get("type") not in ("page_break", None)]
    assert len(ids) == len(set(ids))  # 모든 블록에 겹치지 않는 id가 있다
    g = to_graph(doc)
    node_ids = [n["id"] for n in g["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    assert all(e["source"] in set(node_ids) and e["target"] in set(node_ids) for e in g["edges"])


def test_parse_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    doc = parse(FIX / "SimpleTable.hwpx")
    assert doc["blocks"][0]["type"] == "table" and list(tmp_path.iterdir()) == []
    assert "<table>" in to_markdown(doc)


def test_metadata_keys_cannot_break_document_node():
    g = to_graph({"source": {"name": "a.hwpx", "sha256": "x"}, "blocks": [],
                  "metadata": {"name": "메타 이름", "id": "bad", "type": "bad", "nid": "1", "title": "제목"}})
    d = g["nodes"][0]
    assert (d["id"], d["type"], d["name"], d["title"]) == ("doc", "Document", "a.hwpx", "제목")

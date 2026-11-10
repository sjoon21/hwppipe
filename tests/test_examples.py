"""examples/가 API 변경으로 깨지지 않는지 확인한다."""
import importlib.util
from pathlib import Path

import pytest
from helpers import FIX

from hwppipe import parse
from hwppipe.writer import _iter

_spec = importlib.util.spec_from_file_location("chunk_rag", Path(__file__).parents[1] / "examples/chunk_rag.py")
chunk_rag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chunk_rag)


@pytest.mark.parametrize("src", sorted(FIX.glob("*.hwpx")), ids=lambda p: p.name)
def test_chunk_example_runs_and_links_back(src):
    doc = parse(src)
    ids = {b.get("id") for top in doc["blocks"] for b in _iter([top])}
    for c in chunk_rag.chunks(doc, 300):
        assert c["text"].strip() and c["metadata"]["block_ids"]
        assert set(c["metadata"]["block_ids"]) <= ids


def test_footnotes_are_inlined():
    doc = {"source": {"name": "a", "sha256": "0" * 64}, "notes": [{"id": "fn-1", "kind": "footnote", "blocks": [
        {"type": "paragraph", "text": "각주 내용"}]}],
           "blocks": [{"type": "paragraph", "id": "p-1", "text": "본문[^fn-1]", "heading_path": [],
                       "loc": {"section": 0}}]}
    assert chunk_rag.chunks(doc)[0]["text"] == "본문(주: 각주 내용)"


def _doc(blocks):
    return {"source": {"name": "a", "sha256": "0" * 64}, "notes": [], "blocks": blocks}


def _b(i, t, text, path, **kw):
    return {"type": t, "id": f"x-{i}", "text": text, "heading_path": path, "loc": {"section": 0}, **kw}


def test_chunks_keep_list_numbers_and_do_not_repeat_or_isolate_headings():
    doc = _doc([_b(1, "heading", "개요", ["1. 개요"], prefix="1.", level=1),
                _b(2, "list_item", "첫째 항목", ["1. 개요"], prefix="가.", level=1),
                _b(3, "heading", "빈 절", ["2. 빈 절"], prefix="2.", level=1),
                _b(4, "heading", "본문 절", ["3. 본문 절"], prefix="3.", level=1),
                _b(5, "paragraph", "내용", ["3. 본문 절"])])
    cs = chunk_rag.chunks(doc)
    assert [c["text"] for c in cs] == ["1. 개요\n\n가. 첫째 항목", "3. 본문 절\n\n내용"]
    assert cs[0]["metadata"]["block_ids"] == ["x-1", "x-2"]


def test_max_chars_counts_output_text():
    doc = _doc([_b(i, "paragraph", "가" * 100 + "[^fn-1]", []) for i in range(5)])
    doc["notes"] = [{"id": "fn-1", "kind": "footnote", "blocks": [{"type": "paragraph", "text": "나" * 100}]}]
    assert all(len(c["text"]) <= 300 for c in chunk_rag.chunks(doc, 300))


def test_long_table_is_split_by_rows_with_header():
    cells = [{"row": r, "col": c, "rowspan": 1, "colspan": 1, "header": r == 0,
              "blocks": [{"type": "paragraph", "text": f"{'머리' if r == 0 else '값' * 20}{r}{c}"}]}
             for r in range(30) for c in range(2)]
    t = {"type": "table", "id": "tbl-001", "rows": 30, "cols": 2, "cells": cells, "caption": None,
         "heading_path": ["표 절"], "loc": {"section": 0}}
    cs = chunk_rag.chunks(_doc([t]), 400)
    assert len(cs) > 1 and all(len(c["text"]) <= 400 for c in cs)
    assert all("| 머리00 | 머리01 |" in c["text"] and "| --- | --- |" in c["text"] for c in cs)
    assert all(c["metadata"]["block_ids"] == ["tbl-001"] for c in cs)
    body = [ln for c in cs for ln in c["text"].splitlines() if ln.startswith("| 값")]
    assert len(body) == 29  # 행을 잃거나 겹치지 않는다

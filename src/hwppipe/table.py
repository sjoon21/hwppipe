"""표 격자 복원. 병합으로 가려진 셀은 XML에 없으므로 cellAddr·cellSpan으로 배치한다.

body를 import하지 않는다. 문단 처리 함수는 walk 인자로 받는다(순환 import 방지).
"""
from collections.abc import Callable

from .xml import children, local, q


def parse_caption(obj, ctx, loc: dict, walk: Callable) -> tuple[str | None, str | None]:
    cap = obj.find(q("hp", "caption"))
    if cap is None:
        return None, None
    sub = cap.find(q("hp", "subList"))
    ctx.aside_depth += 1  # 캡션 글은 메모의 붙은 글이 아니다
    try:
        blocks = walk(sub, ctx, {**loc, "in": "caption"}) if sub is not None else []
    finally:
        ctx.aside_depth -= 1
    text = "\n".join(b["text"] for b in blocks if "text" in b)
    return (text or None), cap.get("side")


# 속성값만 큰 표(rowCnt=100000 등)가 격자 계산으로 시간·메모리를 소모하지 못하게 한다. 실제 한글 표는 수천 칸 수준이다.
MAX_TABLE_SLOTS = 250_000
MAX_GRID_WARNINGS = 5


def parse_table(tbl, ctx, loc: dict, walk: Callable) -> dict:
    tid = ctx.new_id("tbl")
    caption, side = parse_caption(tbl, ctx, loc, walk)
    cells, fills = [], []
    for tr in children(tbl):
        if local(tr) != "tr":
            continue
        for tc in children(tr):
            if local(tc) != "tc":
                continue
            addr = tc.find(q("hp", "cellAddr"))
            span = tc.find(q("hp", "cellSpan"))
            r, c = int(addr.get("rowAddr", 0)), int(addr.get("colAddr", 0))
            sub = tc.find(q("hp", "subList"))
            fills.append(tc.get("borderFillIDRef"))
            cells.append({
                "row": r, "col": c,
                "rowspan": int(span.get("rowSpan", 1)) if span is not None else 1,
                "colspan": int(span.get("colSpan", 1)) if span is not None else 1,
                "header": tc.get("header") == "1",
                "blocks": walk(sub, ctx, {"section": loc["section"], "in": f"{tid}[{r},{c}]"}) if sub is not None else [],
            })
    cells.sort(key=lambda x: (x["row"], x["col"]))
    n_rows = max([int(tbl.get("rowCnt", 0)), *(c["row"] + c["rowspan"] for c in cells)])
    n_cols = max([int(tbl.get("colCnt", 0)), *(c["col"] + c["colspan"] for c in cells)])
    if n_rows * n_cols > MAX_TABLE_SLOTS:
        raise ValueError(f"table grid too large: {n_rows}x{n_cols}")  # 처리기가 이 표만 손실로 기록한다
    block = {"type": "table", "id": tid, "rows": int(tbl.get("rowCnt", 0)), "cols": int(tbl.get("colCnt", 0)),
             "caption": caption, "caption_side": side, "cells": cells, "loc": dict(loc),
             # 보이는 선이 하나도 없는 틀 표(쪽 배치용). 테두리 정보가 없는 셀이 있으면 판정하지 않는다.
             "layout": bool(fills) and all(f in ctx.header.invisible_border_fills for f in fills)}
    errors = check_grid(block)
    ctx.warnings += [f"{tid}: {e}" for e in errors[:MAX_GRID_WARNINGS]]
    if len(errors) > MAX_GRID_WARNINGS:
        ctx.warnings.append(f"{tid}: 격자 오류 외 {len(errors) - MAX_GRID_WARNINGS}건")
    return block


def check_grid(block: dict) -> list[str]:
    rows, cols = block["rows"], block["cols"]
    owner: dict[tuple[int, int], tuple[int, int]] = {}
    errors = []
    for c in block["cells"]:
        for r in range(c["row"], c["row"] + c["rowspan"]):
            for k in range(c["col"], c["col"] + c["colspan"]):
                if r >= rows or k >= cols:
                    errors.append(f"cell ({c['row']},{c['col']}) out of range at ({r},{k})")
                elif (r, k) in owner:
                    errors.append(f"overlap at ({r},{k})")
                else:
                    owner[(r, k)] = (c["row"], c["col"])
    errors += [f"empty slot ({r},{k})" for r in range(rows) for k in range(cols) if (r, k) not in owner]
    return errors

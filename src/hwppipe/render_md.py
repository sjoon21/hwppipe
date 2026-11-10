"""document.json 형태의 dict를 Markdown으로 만든다. 표는 병합 셀을 살리기 위해 HTML로 쓴다."""
import re
from html import escape

_APPLY = {"BOTH": "양쪽", "ODD": "홀수 쪽", "EVEN": "짝수 쪽"}
_KIND = {"header": "머리말", "footer": "꼬리말"}


def _label(b: dict) -> str:
    return f"{b['prefix']} {b['text']}" if b.get("prefix") else b["text"]


def _eq_captions(b: dict) -> list[str]:
    return [eq["caption"] for eq in b.get("equations", []) if eq.get("caption")]


def _cell_html(blocks: list[dict]) -> str:
    parts = []
    for b in blocks:
        t = b["type"]
        if t in ("paragraph", "heading", "list_item"):
            parts.append("<br>".join(escape(x) for x in [_label(b), *_eq_captions(b)]))
        elif t == "figure":
            alt = f"{b['id']}: {b['caption']}" if b.get("caption") else b["id"]
            parts.append(f'<img src="{escape(b.get("file") or "missing")}" alt="{escape(alt)}">')
        elif t == "table":
            cap = escape(b["caption"]) if b.get("caption") else ""
            top = b.get("caption_side") == "TOP"
            parts.append((cap + "<br>" if cap and top else "") + table_html(b) + ("<br>" + cap if cap and not top else ""))
        elif t == "textbox":
            cap = [escape(b["caption"])] if b.get("caption") else []
            inner = [_cell_html(b["blocks"])] if b["blocks"] else []
            parts.append("<br>".join(cap + inner if b.get("caption_side") == "TOP" else inner + cap))
    return "<br>".join(parts)


def table_html(block: dict) -> str:
    rows = []
    # rowCnt가 실제 셀보다 작게 기록된 문서에서도 셀을 잃지 않게 실제 셀 범위까지 그린다
    n_rows = max([block["rows"], *(c["row"] + c["rowspan"] for c in block["cells"])])
    for r in range(n_rows):
        tds = []
        for c in block["cells"]:
            if c["row"] != r:
                continue
            tag = "th" if c["header"] else "td"
            attrs = (f' rowspan="{c["rowspan"]}"' if c["rowspan"] > 1 else "") + \
                    (f' colspan="{c["colspan"]}"' if c["colspan"] > 1 else "")
            tds.append(f"<{tag}{attrs}>{_cell_html(c['blocks'])}</{tag}>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return "<table>" + "".join(rows) + "</table>"


def _gfm_cell(blocks: list[dict], nested: list[dict]) -> str:
    # GFM 셀은 한 줄이어야 한다. 셀 안 표는 참조만 남기고 부모 표 뒤에 따로 그린다.
    parts = []
    for b in blocks:
        t = b["type"]
        if t in ("paragraph", "heading", "list_item"):
            parts.append(" ".join([_label(b), *_eq_captions(b)]))
        elif t == "figure":
            alt = f"{b['id']}: {b['caption']}" if b.get("caption") else b["id"]
            parts.append(f"![{alt}]({b.get('file') or 'missing'})")
        elif t == "table":
            nested.append(b)
            parts.append(f"[표 {b['id']}]")
        elif t == "textbox":
            parts.append(_gfm_cell(b["blocks"], nested) + (f" {b['caption']}" if b.get("caption") else ""))
    return " ".join(" ".join(parts).split("\n")).replace("\\", "\\\\").replace("|", "\\|").strip()


def table_gfm(block: dict) -> tuple[str, list[dict]]:
    """HTML 없이 GFM 파이프 표로 그린다. 병합은 시작 셀에 [병합 행×열]로 남기고 가려진 칸은 비운다.
    셀 안 표는 참조만 남기고 목록으로 돌려준다. 부모 캡션 뒤에 따로 그려야 하기 때문이다."""
    nested: list[dict] = []
    n_rows = max([block["rows"], *(c["row"] + c["rowspan"] for c in block["cells"])])
    n_cols = max([block["cols"], *(c["col"] + c["colspan"] for c in block["cells"])])
    grid = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    for c in block["cells"]:
        text = _gfm_cell(c["blocks"], nested)
        if c["rowspan"] > 1 or c["colspan"] > 1:
            text = f"{text} [병합 {c['rowspan']}×{c['colspan']}]".strip()
        grid[c["row"]][c["col"]] = f"{grid[c['row']][c['col']]} {text}".strip()  # 손상 문서의 겹친 셀도 글을 잃지 않는다
    if not n_cols:
        return "", nested  # 셀이 없는 표는 GFM으로 그릴 수 없다(구분선이 없으면 문단이 된다)
    lines = ["| " + " | ".join(row) + " |" for row in grid]
    lines.insert(1, "| " + " | ".join(["---"] * n_cols) + " |")
    return "\n".join(lines), nested


def _table_md(b: dict, fmt: str, marker: str | None = None) -> str:
    out = [marker or f"<!-- table:{b['id']} -->"]
    top = b.get("caption_side") == "TOP"
    if b.get("caption") and top:
        out.append(b["caption"])
    nested: list[dict] = []
    if fmt == "gfm":
        grid, nested = table_gfm(b)
        out += [grid] if grid else []
    else:
        out.append(b.get("html") or table_html(b))
    if b.get("caption") and not top:
        out.append(b["caption"])
    # GFM 표는 빈 줄까지 이어지므로 캡션·다음 표와 빈 줄로 떼어야 표의 행으로 읽히지 않는다
    sep = "\n\n" if fmt == "gfm" else "\n"
    return sep.join(out + [_table_md(t, fmt, f"<!-- table:{t['id']} ({b['id']} 안) -->") for t in nested])


def _plain(blocks: list[dict], fmt: str = "html") -> str:
    # 글상자·각주·머리말 안의 표와 그림도 버리지 않고 그린다
    return "\n".join(_block(b, fmt) for b in blocks)


def _quote(label: str, text: str) -> str:
    lines = text.split("\n") or [""]
    return "\n".join([f"> [{label}] {lines[0]}", *[f"> {x}" for x in lines[1:]]])


_RULE = re.compile(r"=+|-+|(?:\*\s*){3,}|(?:_\s*){3,}")


def _md_line(line: str) -> str:
    # 앞 공백 4칸·탭은 코드 블록이, 줄 앞 #은 제목이 되므로 Markdown에서만 바꾼다(document.json은 원문 유지)
    line = line.lstrip(" \t")
    # 줄 앞 #(제목), =·- 줄(앞 줄을 제목으로 만듦), ***·___(구분선)은 글자 그대로 보이게 한다
    return "\\" + line if line.startswith("#") or _RULE.fullmatch(line.rstrip()) else line


def _md_text(text: str) -> str:
    return "\n".join(_md_line(x) for x in text.split("\n"))


def _block(b: dict, fmt: str = "html") -> str:
    t = b["type"]
    if t == "heading":
        return "\n".join(["#" * min(b["level"], 6) + " " + _label(b), *_eq_captions(b)])
    if t == "list_item":
        marker = "-" if b["prefix"] == "-" else b["prefix"]
        return "\n".join(["  " * (b["level"] - 1) + f"{marker} {b['text']}", *_eq_captions(b)])
    if t == "page_break":
        return "---"
    if t == "figure":
        alt = f"{b['id']}: {b['caption']}" if b.get("caption") else b["id"]
        return f"![{alt}]({b.get('file') or 'missing'})"
    if t == "table":
        return _table_md(b, fmt)
    if t == "textbox":
        cap = [b["caption"]] if b.get("caption") else []
        inner = [_plain(b["blocks"], fmt)] if b["blocks"] else []
        return _quote("글상자", "\n".join(cap + inner if b.get("caption_side") == "TOP" else inner + cap))
    text = _md_text(b["text"])
    for eq in b.get("equations", []):
        text += "\n<!-- hwpeq: " + eq["script"].replace("--", "- -") + " -->"
        if eq.get("caption"):
            text += "\n" + eq["caption"]
    return text


def unframe_layout(blocks: list[dict]) -> list[dict]:
    """틀 표(layout)를 셀 순서대로 풀어 그 안의 블록으로 바꾼 사본을 만든다. 원본 dict는 바꾸지 않는다."""
    out: list[dict] = []
    for b in blocks:
        if b.get("type") == "table" and b.get("layout"):
            cap = [{"type": "paragraph", "text": b["caption"], "loc": b.get("loc", {})}] if b.get("caption") else []
            top = b.get("caption_side") == "TOP"
            out.extend(cap if top else [])
            for c in b["cells"]:
                out.extend(unframe_layout(c["blocks"]))
            out.extend([] if top else cap)
        elif b.get("type") == "table":
            nb = {k: v for k, v in b.items() if k != "html"}  # 셀 안이 바뀌므로 미리 그린 HTML은 버린다
            nb["cells"] = [{**c, "blocks": unframe_layout(c["blocks"])} for c in b["cells"]]
            out.append(nb)
        elif "blocks" in b:
            out.append({**b, "blocks": unframe_layout(b["blocks"])})
        else:
            out.append(b)
    return out


def _indent_rest(text: str) -> str:
    # 각주 정의의 둘째 줄부터 4칸 들여 써야 표·여러 문단이 같은 각주 안에 남는다
    first, *rest = text.split("\n")
    return "\n".join([first, *("    " + x if x else x for x in rest)])


def render(doc: dict, table_format: str = "html", unframe_layout_tables: bool = False) -> str:
    if table_format not in ("html", "gfm"):
        raise ValueError(f"table_format은 html 또는 gfm이어야 합니다: {table_format}")
    if unframe_layout_tables:
        doc = {**doc, "blocks": unframe_layout(doc["blocks"]),
               "headers_footers": [{**h, "blocks": unframe_layout(h["blocks"])} for h in doc.get("headers_footers", [])],
               "notes": [{**n, "blocks": unframe_layout(n["blocks"])} for n in doc.get("notes", [])]}
    hf_by_section: dict[int, list[dict]] = {}
    for hf in doc.get("headers_footers", []):
        hf_by_section.setdefault(hf["section"], []).append(hf)
    out: list[str] = []

    def flush(upto: float) -> None:
        # 구역의 첫 블록 앞에 그 구역(과 블록 없이 지나간 앞 구역)의 머리말·꼬리말을 쓴다
        for sec in sorted(s for s in hf_by_section if s <= upto):
            for hf in hf_by_section.pop(sec):
                out.append(_quote(f"{_KIND[hf['kind']]} · {_APPLY.get(hf['apply'], hf['apply'])}",
                                  _plain(hf["blocks"], table_format)))

    for b in doc["blocks"]:
        flush(b.get("loc", {}).get("section", 0))
        out.append(_block(b, table_format))
    flush(float("inf"))
    for h in doc.get("hidden_comments", []):
        out.append(_quote("숨은 설명", _md_text(h["text"])))
    for m in doc.get("memos", []):
        label = " · ".join(x for x in ("메모", m.get("author"), (m.get("created") or "")[:10]) if x)
        out.append(_quote(label, _md_text(m["text"]) + (f"\n붙은 글: {m['anchor']}" if m.get("anchor") else "")))
    for n in doc.get("notes", []):
        out.append(f"[^{n['id']}]: " + _indent_rest(_plain(n["blocks"], table_format)))
    return "\n\n".join(out) + "\n"

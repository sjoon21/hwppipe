"""document.json을 지식 그래프(노드·엣지)로 바꾼다. 온톨로지 구축이나 그래프 DB 적재에 쓴다.

노드: Document, Section, Heading, Paragraph, ListItem, Table, Cell, Figure, TextBox, Equation,
      Footnote, Endnote, Header, Footer, Memo, HiddenComment
엣지: HAS_SECTION, CONTAINS, NEXT, HAS_CELL, HAS_EQUATION, REFERS_TO, HAS_NOTE, HAS_HEADER, HAS_FOOTER, ANNOTATES
"""
import json
import re

_TYPE = {"paragraph": "Paragraph", "heading": "Heading", "list_item": "ListItem", "table": "Table",
         "figure": "Figure", "textbox": "TextBox"}
_NOTE_REF = re.compile(r"\[\^((?:fn|en)-\d+)\]")
GRAPH_SCHEMA_VERSION = "1"


def _key(loc: dict | None) -> str:
    return json.dumps(loc or {}, sort_keys=True)


def to_graph(doc: dict) -> dict:
    """document.json dict를 {"nodes": [...], "edges": [...]}로 바꾼다. 노드 id는 document.json의 블록 id와 같다."""
    nodes: list[dict] = []
    edges: list[dict] = []
    first_at_loc: dict[str, str] = {}  # 원본 위치 → 그 위치의 첫 블록(메모·숨은 설명이 가리킬 대상)
    n_eq = 0

    def node(nid: str, ntype: str, /, **props) -> None:
        # 그래프 DB 속성은 dict를 담지 못하므로 loc을 loc_section·loc_para·loc_in으로 펼친다
        props.update({f"loc_{k}": v for k, v in (props.pop("loc", None) or {}).items()})
        # id·type은 props(문서 메타데이터 등)가 덮어쓰지 못하게 한다
        nodes.append({"id": nid, "type": ntype,
                      **{k: v for k, v in props.items() if v is not None and k not in ("id", "type")}})

    def edge(src: str, dst: str, etype: str) -> None:
        edges.append({"source": src, "target": dst, "type": etype})

    def block(b: dict, parent: str) -> str | None:
        nonlocal n_eq
        t = b.get("type")
        if t not in _TYPE:
            return None
        props: dict = {"text": b.get("text"), "loc": b.get("loc"), "heading_path": b.get("heading_path") or None}
        if t in ("heading", "list_item"):
            props.update(level=b.get("level"), prefix=b.get("prefix"))
        if t in ("table", "figure", "textbox"):
            props["caption"] = b.get("caption")
        if t == "table":
            props.update(rows=b["rows"], cols=b["cols"], layout=b.get("layout"))
        if t == "figure":
            props.update(file=b.get("file"), original_name=b.get("original_name"))
        node(b["id"], _TYPE[t], **props)
        edge(parent, b["id"], "CONTAINS")
        first_at_loc.setdefault(_key(b.get("loc")), b["id"])
        for eq in b.get("equations", []):
            n_eq += 1
            eid = f"eq-{n_eq:03d}"
            node(eid, "Equation", script=eq["script"], latex=eq.get("latex"), caption=eq.get("caption"))
            edge(b["id"], eid, "HAS_EQUATION")
        for m in _NOTE_REF.finditer(b.get("text") or ""):
            edge(b["id"], m.group(1), "REFERS_TO")
        for c in b.get("cells", []):
            cid = f"{b['id']}[{c['row']},{c['col']}]"
            node(cid, "Cell", row=c["row"], col=c["col"], rowspan=c["rowspan"], colspan=c["colspan"],
                 header=c["header"])
            edge(b["id"], cid, "HAS_CELL")
            children(c["blocks"], cid)
        if t == "textbox":
            children(b["blocks"], b["id"])
        return b["id"]

    def children(blocks: list[dict], parent: str) -> None:
        prev = None
        for b in blocks:
            bid = block(b, parent)
            if bid and prev:
                edge(prev, bid, "NEXT")
            prev = bid or prev

    src = doc.get("source", {})
    node("doc", "Document", **{**doc.get("metadata", {}), "name": src.get("name"), "sha256": src.get("sha256")})
    sections = sorted({b.get("loc", {}).get("section", 0) for b in doc["blocks"]} |
                      {h["section"] for h in doc.get("headers_footers", [])} |
                      {x["loc"].get("section", 0) for x in doc.get("memos", []) + doc.get("hidden_comments", [])})
    for s in sections:
        node(f"sec-{s}", "Section", index=s)
        edge("doc", f"sec-{s}", "HAS_SECTION")

    # 본문: 제목 수준으로 계층을 만들고, 제목이 아닌 블록은 가장 가까운 앞 제목(없으면 구역)에 넣는다.
    # 한글의 구역은 주로 용지 방향·단 설정으로 나뉘므로 제목 계층은 구역을 넘어 이어진다(heading_path와 같다).
    stack: list[tuple[int, str]] = []
    prev = None
    for b in doc["blocks"]:
        sec = b.get("loc", {}).get("section", 0)
        if b.get("type") == "heading":
            while stack and stack[-1][0] >= b["level"]:
                stack.pop()
        bid = block(b, stack[-1][1] if stack else f"sec-{sec}")
        if bid is None:
            continue
        if b.get("type") == "heading":
            stack.append((b["level"], bid))
        if prev:
            edge(prev, bid, "NEXT")
        prev = bid

    for n in doc.get("notes", []):
        node(n["id"], "Footnote" if n["kind"] == "footnote" else "Endnote")
        edge("doc", n["id"], "HAS_NOTE")
        children(n["blocks"], n["id"])
    n_hf: dict[str, int] = {}
    for h in doc.get("headers_footers", []):
        n_hf[h["kind"]] = n_hf.get(h["kind"], 0) + 1
        hid = f"{h['kind']}-{n_hf[h['kind']]:03d}"
        node(hid, h["kind"].capitalize(), apply=h.get("apply"))
        edge(f"sec-{h['section']}", hid, "HAS_HEADER" if h["kind"] == "header" else "HAS_FOOTER")
        children(h["blocks"], hid)
    for i, c in enumerate(doc.get("hidden_comments", []), 1):
        cid = f"hidden-{i:03d}"
        node(cid, "HiddenComment", text=c["text"], loc=c["loc"])
        edge(cid, first_at_loc.get(_key(c["loc"]), f"sec-{c['loc'].get('section', 0)}"), "ANNOTATES")
    for m in doc.get("memos", []):
        node(m["id"], "Memo", text=m["text"], author=m.get("author"), created=m.get("created"),
             anchor=m.get("anchor"), loc=m["loc"])
        edge(m["id"], first_at_loc.get(_key(m["loc"]), f"sec-{m['loc'].get('section', 0)}"), "ANNOTATES")

    # 각주 참조가 가리키는 각주가 없으면(깨진 문서) 그 참조 엣지만 내지 않는다
    ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["type"] != "REFERS_TO" or e["target"] in ids]
    return {"schema_version": GRAPH_SCHEMA_VERSION, "nodes": nodes, "edges": edges}

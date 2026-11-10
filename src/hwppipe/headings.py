"""제목 판정과 heading_path. 개요 기능이 있으면 그것을, 없으면 휴리스틱(infer)을 쓴다."""
import re

from .header import Header
from .numbering import Numberer


def _nested(b: dict) -> list[dict]:
    out = [x for c in b.get("cells", []) for x in c["blocks"]]
    return out + b.get("blocks", [])


def _number(blocks: list[dict], n: Numberer, top: bool) -> None:
    # 번호 카운터는 문서 순서로 진행하므로 셀·글상자 안까지 같은 순서로 내려간다
    for b in blocks:
        if b["type"] == "paragraph":
            r = n.prefix(b["_para_pr"])
            if r:
                kind, lvl, pre = r
                b["type"] = "heading" if (top and kind == "OUTLINE") else "list_item"
                b["level"], b["prefix"] = lvl + 1, pre
                if b["type"] == "heading":
                    b["heading_source"] = "outline"
        _number(_nested(b), n, False)


def _label(b: dict) -> str:
    return f"{b['prefix']} {b['text']}" if b.get("prefix") else b["text"]


def assign(sections: list[tuple[list[dict], str | None]], header: Header) -> list[dict]:
    n = Numberer(header, None)
    out: list[dict] = []
    for blocks, outline_id in sections:
        n.outline_id = outline_id or "1"  # secPr이 없으면 한컴 기본 개요 번호 정의(1)를 쓴다
        _number(blocks, n, True)
        out.extend(blocks)
    if not any(b["type"] == "heading" for b in out):
        infer(out, header)
    set_heading_paths(out)
    return out


def set_heading_paths(blocks: list[dict]) -> None:
    """최상위 블록마다 속한 제목 목록을 단다. 수준을 건너뛰는 제목(1→3→3)에서도 형제 제목을 상위로 쌓지 않는다."""
    stack: list[tuple[int, str]] = []
    for b in blocks:
        if b["type"] == "heading":
            while stack and stack[-1][0] >= b["level"]:
                stack.pop()
            stack.append((b["level"], _label(b)))
        b["heading_path"] = [label for _, label in stack]


_H = "[가나다라마바사아자차카타파하]"  # [가-하]는 가~하 사이 모든 음절과 일치하므로 쓰지 않는다
# 공문서 표준 위계 순서. 목록의 순서가 곧 수준의 우선순위다.
PATTERNS = [re.compile(p) for p in (
    r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.\s*", r"^\d{1,2}\.(?!\d)\s*", rf"^{_H}\.\s*", r"^\d{1,2}\)\s*",
    rf"^{_H}\)\s*", r"^\(\d{1,2}\)\s*", rf"^\({_H}\)\s*", r"^[①-⑳]\s*",
)]
HEADING_MAX_CHARS = 60
LARGE_TEXT_RATIO = 1.1
LARGE_TEXT_MAX_CHARS = 40
_LABEL_VALUE = re.compile(r":\s*\S")  # "행사장소: 국립…" 같은 항목·값 형태
_BULLETS = tuple("■□▪▫●○◆◇◎▶▷►-·•※⇨→")  # 글머리 기호로 시작하면 제목이 아니라 항목이다
_SENTENCE_ENDINGS = ("다.", "다", "요.", "음.", "함.")


def _is_title_like(text: str, max_chars: int) -> bool:
    t = text.strip()
    return 0 < len(t) <= max_chars and not t.endswith(_SENTENCE_ENDINGS)


def infer(blocks: list[dict], header: Header) -> None:
    """개요 문단이 없는 문서에서 번호 패턴과 글자 모양으로 제목을 추정한다. 최상위 블록만 바꾼다.

    번호 제목이 큰 글자 제목보다 많으면 번호 위계를 뼈대로, 아니면 글자 크기 위계를 뼈대로 수준을 정한다.
    """
    paras = [b for b in blocks if b["type"] == "paragraph"]
    if not paras:
        return
    style = {id(b): header.char_props.get(b["_char_pr"], (1000, False)) for b in paras}
    # 본문 글자 크기: 글자 수로 가중한 중앙값(제목 문단 수가 많아도 본문 크기가 대표값이 되게)
    weighted = sorted((style[id(b)][0], len(b["text"].strip())) for b in paras)
    half, acc, median = sum(n for _, n in weighted) / 2, 0, weighted[0][0]
    for h, n in weighted:
        acc += n
        if acc >= half:
            median = h
            break
    emphasized = lambda b: style[id(b)][1] or style[id(b)][0] >= median * LARGE_TEXT_RATIO

    matched = []
    for b in paras:
        text = b["text"].lstrip()  # 실문서는 공백 문자로 들여쓰기를 한다
        for k, pat in enumerate(PATTERNS):
            m = pat.match(text)
            if m:
                rest = text[m.end():]
                ok = _is_title_like(rest, HEADING_MAX_CHARS) and not _LABEL_VALUE.search(rest)
                matched.append((b, k, m.group(0).strip(), rest, ok))
                break
    # 문서가 번호 제목을 굵게·크게 강조한다면, 강조되지 않은 번호 문단은 목록으로 본다
    if any(ok and emphasized(b) for b, _, _, _, ok in matched):
        matched = [(b, k, pre, rest, ok and emphasized(b)) for b, k, pre, rest, ok in matched]

    numbered = {id(b) for b, *_ in matched}
    big = [b for b in paras if id(b) not in numbered and style[id(b)][0] >= median * LARGE_TEXT_RATIO
           and _is_title_like(b["text"], LARGE_TEXT_MAX_CHARS) and not b["text"].lstrip().startswith(_BULLETS)]
    kinds = sorted({k for _, k, *_ in matched})
    n_numbered = sum(1 for *_, ok in matched if ok)
    if n_numbered > len(big):
        # 번호가 뼈대인 문서: 큰 글자는 문서 제목이나 표지·서식 제목이다.
        # 번호 제목보다 앞에 한 번만 나오는 가장 큰 글자만 문서 제목(1수준)으로 올리고,
        # 나머지 큰 글자는 최상위 번호 제목과 같은 수준에 둔다(번호 위계를 밀어내지 않게).
        pos = {id(b): i for i, b in enumerate(blocks)}
        first_num = min(pos[id(b)] for b, *_, ok in matched if ok)
        top_h = max((style[id(b)][0] for b in big), default=None)
        at_top = [b for b in big if style[id(b)][0] == top_h]
        title = at_top[0] if len(at_top) == 1 and pos[id(at_top[0])] < first_num else None
        base = 1 if title else 0
        for b in big:
            b.update(type="heading", level=1 if b is title else base + 1, prefix=None, heading_source="inferred")
        rank = {k: base + i + 1 for i, k in enumerate(kinds)}
    else:
        # 글자 크기가 뼈대인 문서: 큰 글자를 크기순 수준으로 두고 번호 제목은 그 아래에 둔다
        tiers = {h: i + 1 for i, h in enumerate(sorted({style[id(b)][0] for b in big}, reverse=True))}
        for b in big:
            b.update(type="heading", level=min(tiers[style[id(b)][0]], 6), prefix=None, heading_source="inferred")
        rank = {k: len(tiers) + i + 1 for i, k in enumerate(kinds)}
    for b, k, pre, rest, ok in matched:
        b.update(type="heading" if ok else "list_item", prefix=pre, text=rest, level=min(rank[k], 6))
        if ok:
            b["heading_source"] = "inferred"

"""구역 XML을 순회해서 JSON으로 직렬화할 수 있는 블록 dict 목록을 만든다."""
import re
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field

from .equation import to_latex
from .header import Header
from .numbering import format_number
from .package import Package
from .table import parse_caption, parse_table
from .xml import children, local, parse, q

# 조판 정보나 마커일 뿐 내용이 없는 요소. 손실로 세지 않는다.
IGNORED = {
    "linesegarray", "secPr", "colPr", "markpenBegin", "markpenEnd", "titleMark", "bookmark",
    "fieldBegin", "fieldEnd", "insertBegin", "insertEnd",
}
_INLINE_CHARS = {"tab": "\t", "lineBreak": "\n", "nbSpace": " ", "fwSpace": " ", "hypen": "-", "hyphen": "-"}
_T = q("hp", "t")
_DRAWABLE = {"pic", "rect", "ellipse", "line", "arc", "polygon", "curve", "connectLine", "container", "textart",
             "ole", "video", "chart", "equation", "tbl", "compose", "dutmal", "btn", "radioBtn", "checkBtn",
             "comboBox", "listBox", "edit", "scrollBar"}


@dataclass
class Ctx:
    pkg: Package
    header: Header
    losses: dict[str, list[dict]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[dict] = field(default_factory=list)
    headers_footers: list[dict] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)
    chars_source: int = 0
    chars_emitted: int = 0
    hidden_comments: list[dict] = field(default_factory=list)
    memos: list[dict] = field(default_factory=list)
    open_memos: dict[str, dict] = field(default_factory=dict)  # fieldBegin id → 아직 fieldEnd를 만나지 않은 메모
    aside_depth: int = 0  # 메모·각주·캡션·머리말처럼 본문 밖 글을 읽는 중이면 그 글자는 메모의 붙은 글이 아니다
    deleting: set[str] = field(default_factory=set)
    skip_delete: set[str] = field(default_factory=set)
    deleted_chars: int = 0
    section: int = 0

    def new_id(self, kind: str) -> str:
        n = self.counters[kind] = self.counters.get(kind, 0) + 1
        return f"{kind}-{n}" if kind in ("fn", "en") else f"{kind}-{n:03d}"

    def loss(self, kind: str, loc: dict, chars: int = 0) -> None:
        self.losses.setdefault(kind, []).append({"loc": dict(loc), "chars": chars})
        self.chars_source += chars

    def mark(self) -> tuple:
        """실패한 처리를 되돌릴 수 있게 누적 상태를 기록한다."""
        return (self.chars_source, self.chars_emitted, self.deleted_chars, set(self.deleting),
                len(self.notes), len(self.headers_footers), len(self.hidden_comments), len(self.memos), len(self.warnings),
                {k: len(v) for k, v in self.losses.items()},
                {k: (m, m["anchor"]) for k, m in self.open_memos.items()})

    def rollback(self, m: tuple) -> None:
        (self.chars_source, self.chars_emitted, self.deleted_chars, self.deleting,
         n_notes, n_hf, n_hidden, n_memo, n_warn, losses, open_memos) = m
        del self.notes[n_notes:], self.headers_footers[n_hf:], self.hidden_comments[n_hidden:], self.warnings[n_warn:]
        del self.memos[n_memo:]
        self.open_memos = {k: memo for k, (memo, _) in open_memos.items()}
        for memo, anchor in open_memos.values():
            memo["anchor"] = anchor
        for k in list(self.losses):
            if k in losses:
                del self.losses[k][losses[k]:]
            else:
                del self.losses[k]


@dataclass
class ParaState:
    """문단 하나를 처리하는 동안 모으는 값. 개체 처리기가 text·objects·equations에 덧붙인다."""
    loc: dict
    parts: list[str] = field(default_factory=list)
    objects: list[dict] = field(default_factory=list)
    equations: list[dict] = field(default_factory=list)
    run_chars: dict[str, int] = field(default_factory=dict)


# run 자식 요소의 처리기: local name → fn(el, ctx, state). Task 4 이후 처리기가 여기에 등록된다.
HANDLERS: dict[str, Callable] = {}
# hp:ctrl 자식 요소의 처리기
CTRL_HANDLERS: dict[str, Callable] = {}


def t_chars(el) -> int:
    return sum(len("".join(t.itertext())) for t in el.iter(_T))


def _emit(ctx: Ctx, state: ParaState, s: str, char_pr: str) -> None:
    if not s:
        return
    if ctx.deleting:
        ctx.deleted_chars += len(s)
        return
    ctx.chars_source += len(s)
    ctx.chars_emitted += len(s)
    _put(ctx, state, s)
    state.run_chars[char_pr] = state.run_chars.get(char_pr, 0) + len(s)


def _put(ctx: Ctx, state: ParaState, s: str) -> None:
    """출력 글자를 문단에 넣고, 열린 메모의 붙은 글에도 넣는다. 글자 수 집계는 호출한 쪽이 맡는다."""
    state.parts.append(s)
    if ctx.open_memos and not ctx.aside_depth:
        for m in ctx.open_memos.values():
            m["anchor"] = (m["anchor"] or "") + s


def _anchor_break(ctx: Ctx) -> None:
    # 메모가 문단·셀 경계를 넘으면 붙은 글에도 줄바꿈을 남긴다. 앞뒤 줄바꿈은 메모를 닫을 때 지운다.
    if ctx.aside_depth:
        return
    for m in ctx.open_memos.values():
        if m["anchor"] and not m["anchor"].endswith("\n"):
            m["anchor"] += "\n"


def _close_memo(m: dict) -> None:
    m["anchor"] = (m["anchor"] or "").strip("\n") or None


def _drop_unended(ctx: Ctx, keep: set[str]) -> None:
    """fieldEnd 없이 끝난 메모는 붙은 글의 범위를 알 수 없으므로 비우고 경고한다."""
    for k in [k for k in ctx.open_memos if k not in keep]:
        m = ctx.open_memos.pop(k)
        m["anchor"] = None
        ctx.warnings.append(f"{m['id']}: fieldEnd 없음, 붙은 글을 비움")


@contextmanager
def aside(ctx: Ctx):
    ctx.aside_depth += 1
    try:
        yield
    finally:
        ctx.aside_depth -= 1


def _read_t(t, ctx: Ctx, state: ParaState, char_pr: str) -> None:
    _emit(ctx, state, t.text or "", char_pr)
    for c in t:
        name = local(c)
        if name == "deleteBegin":
            if c.get("Id", "") not in ctx.skip_delete:  # 짝이 없는 시작 마커는 무시한다
                ctx.deleting.add(c.get("Id", ""))
        elif name == "deleteEnd":
            ctx.deleting.discard(c.get("Id", ""))
        elif name in _INLINE_CHARS and not ctx.deleting:
            _put(ctx, state, _INLINE_CHARS[name])  # hwppipe가 만든 문자이므로 글자 수에 세지 않는다
        _emit(ctx, state, c.tail or "", char_pr)


def _hidden_comment(el, ctx: Ctx, state: ParaState) -> None:
    sub = el.find(q("hp", "subList"))
    with aside(ctx):
        blocks = walk_paragraphs(sub, ctx, {**state.loc, "in": "hidden"}) if sub is not None else []
    text = "\n".join(b["text"] for b in blocks if "text" in b)
    ctx.hidden_comments.append({"loc": dict(state.loc), "text": text})


CTRL_HANDLERS["hiddenComment"] = _hidden_comment


def _field(el, ctx: Ctx, state: ParaState) -> None:
    # 한글 메모는 fieldBegin(type=MEMO)의 subList에 들어 있다. 다른 필드의 글자는 아직 처리하지 않으므로 손실로 센다.
    if el.get("type", "").upper() != "MEMO":
        if t_chars(el):
            ctx.loss("fieldBegin", state.loc, t_chars(el))
        return
    params = {p.get("name"): (p.text or "") for p in el.iter(q("hp", "stringParam"), q("hp", "integerParam"))}
    sub = el.find(q("hp", "subList"))
    keep = set(ctx.open_memos)
    with aside(ctx):
        blocks = walk_paragraphs(sub, ctx, {**state.loc, "in": "memo"}) if sub is not None else []
    _drop_unended(ctx, keep)  # 메모 본문 안에서 열리고 닫히지 않은 메모
    number = params.get("Number", "")
    memo = {"id": ctx.new_id("memo"), "author": params.get("Author") or None,
            "created": params.get("CreateDateTime") or None,
            "number": int(number) if number.isdigit() else None, "loc": dict(state.loc),
            "text": "\n".join(b["text"] for b in blocks if "text" in b), "anchor": None}
    ctx.memos.append(memo)
    if el.get("id"):  # id가 없으면 짝 fieldEnd를 찾을 수 없으므로 붙은 글을 모으지 않는다
        ctx.open_memos[el.get("id")] = memo  # 짝 fieldEnd까지 본문 글자를 붙은 글(anchor)로 모은다


def _field_end(el, ctx: Ctx, state: ParaState) -> None:
    m = ctx.open_memos.pop(el.get("beginIDRef", ""), None)
    if m:
        _close_memo(m)


# 캡션의 "그림 1"·"표 2" 번호. 쪽 번호(PAGE)는 저장된 값이 쪽마다 다르므로 글자로 내지 않는다.
_AUTONUM_TYPES = {"PICTURE", "TABLE", "EQUATION"}


def _auto_num(el, ctx: Ctx, state: ParaState) -> None:
    num = el.get("num", "")
    if el.get("numType") not in _AUTONUM_TYPES or not num.isdigit() or ctx.deleting:
        return
    fmt = el.find(q("hp", "autoNumFormat"))
    get = (lambda k: fmt.get(k, "")) if fmt is not None else (lambda k: "")
    # hwppipe가 원본 번호 정의로 만든 문자이므로 글자 수에 세지 않는다
    _put(ctx, state, get("prefixChar") + format_number(int(num), get("type") or "DIGIT") + get("suffixChar"))


CTRL_HANDLERS["fieldBegin"] = _field
CTRL_HANDLERS["fieldEnd"] = _field_end
CTRL_HANDLERS["autoNum"] = _auto_num


def _guarded(handler: Callable, el, ctx: Ctx, state: ParaState) -> None:
    """개체 하나가 깨져도 구역 전체를 잃지 않게, 그 개체만 손실로 기록하고 계속한다."""
    m, n_parts, n_objs, n_eqs = ctx.mark(), len(state.parts), len(state.objects), len(state.equations)
    try:
        handler(el, ctx, state)
    except Exception as e:
        ctx.rollback(m)
        del state.parts[n_parts:], state.objects[n_objs:], state.equations[n_eqs:]
        ctx.loss(f"broken_{local(el)}", state.loc, t_chars(el))
        ctx.warnings.append(f"broken_{local(el)}: {type(e).__name__}: {e}")


def _run(run, ctx: Ctx, state: ParaState) -> None:
    char_pr = run.get("charPrIDRef", "0")
    for c in children(run):
        name = local(c)
        if name == "t":
            _read_t(c, ctx, state, char_pr)
        elif name == "ctrl":
            for cc in children(c):
                h = CTRL_HANDLERS.get(local(cc))
                if h:
                    _guarded(h, cc, ctx, state)
                elif t_chars(cc):  # 글자가 없는 제어 요소(쪽 번호 등)는 표시일 뿐이고, 글자가 있으면 손실이다
                    ctx.loss(local(cc), state.loc, t_chars(cc))
        elif name in HANDLERS:
            if not ctx.deleting:  # 변경 추적으로 삭제된 구간의 개체는 최종본에 없다
                _guarded(HANDLERS[name], c, ctx, state)
        elif name not in IGNORED:
            ctx.loss(name, state.loc, t_chars(c))


def walk_paragraphs(parent, ctx: Ctx, loc_base: dict) -> list[dict]:
    """parent 바로 아래의 hp:p를 블록 목록으로 바꾼다. 셀·글상자·각주 안에서도 재사용한다."""
    blocks: list[dict] = []
    for j, p in enumerate(c for c in children(parent) if local(c) == "p"):
        state = ParaState({**loc_base, "para": j})
        _anchor_break(ctx)
        for run in children(p):
            if local(run) == "run":
                _run(run, ctx, state)
        _anchor_break(ctx)
        if p.get("pageBreak") == "1":
            blocks.append({"type": "page_break", "loc": state.loc})
        text = "".join(state.parts)
        if not text.strip():  # 공백뿐인 문단은 출력하지 않으므로 원본 집계에서도 뺀다
            blank = sum(state.run_chars.values())
            ctx.chars_source -= blank
            ctx.chars_emitted -= blank
        else:
            char_pr = max(state.run_chars, key=state.run_chars.get) if state.run_chars else "0"
            blocks.append({"type": "paragraph", "text": text, "equations": state.equations,
                           "loc": state.loc, "_para_pr": p.get("paraPrIDRef", "0"), "_char_pr": char_pr})
        blocks.extend(state.objects)
    return blocks


def _table(el, ctx: Ctx, state: ParaState) -> None:
    state.objects.append(parse_table(el, ctx, state.loc, walk_paragraphs))


HANDLERS["tbl"] = _table

_NAME_RE = re.compile(r"원본 그림의 이름:\s*(.+)")
_SIZE_RE = re.compile(r"가로\s*(\d+)\s*pixel,\s*세로\s*(\d+)\s*pixel")


def _picture(el, ctx: Ctx, state: ParaState) -> None:
    img = next(el.iter(q("hc", "img")), None)
    bid = img.get("binaryItemIDRef") if img is not None else None
    item = ctx.pkg.bins.get(bid or "")
    if item is None:
        ctx.loss("missing_binary", state.loc)
    elif not item.embedded:
        ctx.loss("link_picture", state.loc)
    comment = el.findtext(q("hp", "shapeComment")) or ""
    name, size = _NAME_RE.search(comment), _SIZE_RE.search(comment)
    caption, side = parse_caption(el, ctx, state.loc, walk_paragraphs)
    state.objects.append({
        "type": "figure", "id": ctx.new_id("fig"), "binary_id": bid, "caption": caption, "caption_side": side,
        "original_name": name.group(1).strip() if name else None,
        "pixel_size": [int(size.group(1)), int(size.group(2))] if size else None,
        "loc": dict(state.loc),
    })


def _container(el, ctx: Ctx, state: ParaState) -> None:
    # 묶음 개체는 블록을 만들지 않고 안의 그리기 개체만 처리한다. sz·pos 같은 속성 요소는 내용이 아니다.
    for c in children(el):
        name = local(c)
        if name not in _DRAWABLE:
            continue
        if name in HANDLERS:
            _guarded(HANDLERS[name], c, ctx, state)
        else:
            ctx.loss(name, state.loc, t_chars(c))


def _shape(el, ctx: Ctx, state: ParaState) -> None:
    sub = el.find(f"{q('hp', 'drawText')}/{q('hp', 'subList')}")
    caption, side = parse_caption(el, ctx, state.loc, walk_paragraphs)
    if sub is None and caption is None:
        return  # 글자도 캡션도 없는 도형은 내용이 없으므로 손실이 아니다
    bid = ctx.new_id("box")
    blocks = walk_paragraphs(sub, ctx, {"section": state.loc["section"], "in": bid}) if sub is not None else []
    if blocks or caption:
        state.objects.append({"type": "textbox", "id": bid, "blocks": blocks, "caption": caption,
                              "caption_side": side, "loc": dict(state.loc)})


def _equation(el, ctx: Ctx, state: ParaState) -> None:
    script = el.findtext(q("hp", "script")) or ""
    latex = to_latex(script)
    if latex is None:
        ctx.loss("equation_latex", state.loc)
        state.parts.append(f"`{script}`")
    else:
        state.parts.append(f"${latex}$")
    eq = {"script": script, "latex": latex}
    caption, side = parse_caption(el, ctx, state.loc, walk_paragraphs)
    if caption:
        eq.update(caption=caption, caption_side=side)
    state.equations.append(eq)


def _sub_blocks(el, ctx: Ctx, in_id: str) -> list[dict]:
    sub = el.find(q("hp", "subList"))
    with aside(ctx):
        return walk_paragraphs(sub, ctx, {"section": ctx.section, "in": in_id}) if sub is not None else []


def _note(kind: str) -> Callable:
    def handle(el, ctx: Ctx, state: ParaState) -> None:
        nid = ctx.new_id("fn" if kind == "footnote" else "en")
        ctx.notes.append({"id": nid, "kind": kind, "blocks": _sub_blocks(el, ctx, nid)})
        state.parts.append(f"[^{nid}]")
    return handle


def _header_footer(kind: str) -> Callable:
    def handle(el, ctx: Ctx, state: ParaState) -> None:
        ctx.headers_footers.append({"kind": kind, "apply": el.get("applyPageType", "BOTH"),
                                    "section": ctx.section, "blocks": _sub_blocks(el, ctx, kind)})
    return handle


CTRL_HANDLERS["footNote"] = _note("footnote")
CTRL_HANDLERS["endNote"] = _note("endnote")
CTRL_HANDLERS["header"] = _header_footer("header")
CTRL_HANDLERS["footer"] = _header_footer("footer")
HANDLERS["equation"] = _equation
def _textart(el, ctx: Ctx, state: ParaState) -> None:
    # 글맵시 글자는 text 속성에 있고 줄바꿈은 ␍␊ 기호로 저장된다
    text = el.get("text", "").replace("␍␊", "\n")
    if not text.strip():
        return
    n = len(text.replace("\n", ""))
    ctx.chars_source += n
    ctx.chars_emitted += n
    bid = ctx.new_id("box")
    loc = {"section": state.loc["section"], "in": bid, "para": 0}
    state.objects.append({"type": "textbox", "id": bid, "loc": dict(state.loc), "caption": None, "caption_side": None,
                          "blocks": [
        {"type": "paragraph", "text": text, "equations": [], "loc": loc, "_para_pr": "0", "_char_pr": "0"}]})


HANDLERS["textart"] = _textart
HANDLERS["pic"] = _picture
HANDLERS["container"] = _container
for _n in ("rect", "ellipse", "polygon", "arc", "curve", "connectLine", "line"):
    HANDLERS[_n] = _shape


def parse_section(data: bytes, index: int, ctx: Ctx) -> tuple[list[dict], str | None]:
    root = parse(data)
    ctx.section = index
    ctx.deleting = set()
    ctx.open_memos = {}
    begins = {e.get("Id", "") for e in root.iter(q("hp", "deleteBegin"))}
    ends = {e.get("Id", "") for e in root.iter(q("hp", "deleteEnd"))}
    ctx.skip_delete = begins - ends
    if ctx.skip_delete:
        ctx.warnings.append(f"track_changes: 짝이 없는 deleteBegin {len(ctx.skip_delete)}개는 무시함")
    sec_pr = next(root.iter(q("hp", "secPr")), None)
    blocks = walk_paragraphs(root, ctx, {"section": index})
    _drop_unended(ctx, set())
    if ctx.deleted_chars:
        ctx.warnings.append(f"track_changes: {ctx.deleted_chars}자 삭제 구간 제외")
        ctx.deleted_chars = 0
    return blocks, (sec_pr.get("outlineShapeIDRef") if sec_pr is not None else None)

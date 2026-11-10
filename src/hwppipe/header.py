"""header.xml에서 문단 번호 종류·번호 정의·글머리표·글자 모양을 읽는다."""
from dataclasses import dataclass, field

from .xml import parse, q


@dataclass
class Header:
    para_heading: dict[str, tuple[str, str, int]] = field(default_factory=dict)
    numberings: dict[str, dict[int, tuple[str, str, int]]] = field(default_factory=dict)
    bullets: dict[str, str] = field(default_factory=dict)
    char_props: dict[str, tuple[int, bool]] = field(default_factory=dict)
    invisible_border_fills: set[str] = field(default_factory=set)  # 네 변이 모두 NONE인 borderFill id


def parse_header(data: bytes) -> Header:
    root = parse(data)
    # hp:switch의 case 갈래는 default와 같은 내용을 한 번 더 담으므로 지운다
    for case in list(root.iter(q("hp", "case"))):
        case.getparent().remove(case)
    h = Header()
    for pp in root.iter(q("hh", "paraPr")):
        hd = next(pp.iter(q("hh", "heading")), None)
        if hd is not None:
            h.para_heading[pp.get("id")] = (hd.get("type", "NONE"), hd.get("idRef", "0"), int(hd.get("level", "0")))
    for nb in root.iter(q("hh", "numbering")):
        h.numberings[nb.get("id")] = {
            int(ph.get("level")): (ph.get("numFormat", "DIGIT"), ph.text or "", int(ph.get("start", "1")))
            for ph in nb.iter(q("hh", "paraHead"))
        }
    for b in root.iter(q("hh", "bullet")):
        h.bullets[b.get("id")] = b.get("char", "")
    for bf in root.iter(q("hh", "borderFill")):
        sides = [bf.find(q("hh", f"{s}Border")) for s in ("left", "right", "top", "bottom")]
        if all(e is not None and e.get("type") == "NONE" for e in sides):
            # 배경색은 보지 않는다. 실문서에서 테두리 없이 배경만 칠한 표 35개는 대부분 장식용 제목 상자였다.
            h.invisible_border_fills.add(bf.get("id"))
    for cp in root.iter(q("hh", "charPr")):
        h.char_props[cp.get("id")] = (int(cp.get("height", "1000")), cp.find(q("hh", "bold")) is not None)
    return h

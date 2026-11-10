"""자동 번호 계산. HWPX 본문에는 "1.", "가." 같은 번호 글자가 없어서 직접 만들어야 한다."""
import re

from .header import Header

_HANGUL = "가나다라마바사아자차카타파하"
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _roman(n: int) -> str:
    out = ""
    for v, s in _ROMAN:
        while n >= v:
            out, n = out + s, n - v
    return out


def format_number(n: int, fmt: str) -> str:
    if fmt == "HANGUL_SYLLABLE" and 1 <= n <= len(_HANGUL):
        return _HANGUL[n - 1]
    if fmt == "CIRCLED_DIGIT" and 1 <= n <= len(_CIRCLED):
        return _CIRCLED[n - 1]
    if fmt in ("ROMAN_CAPITAL", "ROMAN_SMALL") and 1 <= n <= 3999:
        r = _roman(n)
        return r if fmt == "ROMAN_CAPITAL" else r.lower()
    if fmt in ("LATIN_CAPITAL", "LATIN_SMALL") and 1 <= n <= 26:
        return chr((ord("A") if fmt == "LATIN_CAPITAL" else ord("a")) + n - 1)
    return str(n)


_CARET = re.compile(r"\^(\d)")


class Numberer:
    """문서 순서대로 prefix()를 호출하면 번호 정의별 카운터를 진행시키며 번호 문자열을 만든다."""

    def __init__(self, header: Header, outline_id: str | None):
        self.header = header
        self.outline_id = outline_id
        self.counts: dict[str, dict[int, int]] = {}

    def prefix(self, para_pr_id: str) -> tuple[str, int, str] | None:
        kind, id_ref, level = self.header.para_heading.get(para_pr_id, ("NONE", "0", 0))
        if kind == "BULLET":
            return ("BULLET", level, "-")
        if kind not in ("OUTLINE", "NUMBER"):
            return None
        num_id = self.outline_id if kind == "OUTLINE" else id_ref
        defs = self.header.numberings.get(num_id or "")
        if not defs:
            return None
        k = level + 1
        if k not in defs:
            return None
        start_of = lambda d: defs.get(d, ("DIGIT", "", 1))[2]
        counts = self.counts.setdefault(f"{kind}:{num_id}", {})
        counts[k] = counts[k] + 1 if k in counts else start_of(k)
        for d in [d for d in counts if d > k]:
            del counts[d]
        # 수준을 건너뛰어 내려오면 사이 수준도 시작값으로 확정된다("4." → "4.1.1.1." → "4.1.2.")
        for d in range(1, k):
            counts.setdefault(d, start_of(d))
        tmpl = defs[k][1]
        text = _CARET.sub(lambda m: format_number(counts[int(m.group(1))] if int(m.group(1)) <= k
                                                  else start_of(int(m.group(1))),
                                                  defs.get(int(m.group(1)), ("DIGIT",))[0]), tmpl)
        return (kind, level, text)

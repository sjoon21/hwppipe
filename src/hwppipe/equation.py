"""한컴 수식 스크립트를 LaTeX로 바꾼다.

본 제품은 한컴의 HWP 문서 파일(.hwp) 공개 문서를 참고하여 개발하였습니다.

기호 대응표는 _eqsymbols.py(hml-equation-parser, Apache-2.0)를 쓰고, 구문 해석은 직접 한다.
변환하지 못하면 None을 돌려준다. 호출하는 쪽은 원본 스크립트를 항상 보존한다.
"""
import re

from ._eqsymbols import ACCENTS, MATRICES, SYMBOLS

_EXTRA = {"le": r"\le", "ge": r"\ge", "ne": r"\ne", "leq": r"\le", "geq": r"\ge", "cdot": r"\cdot",
          "pm": r"\pm", "+-": r"\pm", "inf": r"\infty", "<=": r"\le", ">=": r"\ge"}
_TOKEN = re.compile(r'"[^"]*"|<->|<=|>=|->|!=|==|\+-|[A-Za-z]+|\d+(?:\.\d+)?|\S')


class _Fail(Exception):
    pass


def _tokens(script: str) -> list[str]:
    # `와 ~는 한컴 수식의 공백 기호다
    return _TOKEN.findall(script.replace("`", " ").replace("~", " "))


class _Parser:
    def __init__(self, toks: list[str]):
        self.toks, self.i = toks, 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> str:
        if self.i >= len(self.toks):
            raise _Fail("unexpected end")
        self.i += 1
        return self.toks[self.i - 1]

    def seq(self, stop: set[str]) -> list[tuple[str, str]]:
        """항목 목록. 항목은 (종류, LaTeX)이며 종류는 'group' 또는 'item'이다."""
        items: list[tuple[str, str]] = []
        while self.peek() is not None and self.peek() not in stop:
            if self.peek() in ("over", "OVER"):
                self.take()
                if not items:
                    raise _Fail("over without numerator")
                num = items.pop()
                den = self.postfix()
                items.append(("item", rf"\frac{{{_inner(num)}}}{{{_inner(den)}}}"))
            else:
                items.append(self.postfix())
        return items

    def postfix(self) -> tuple[str, str]:
        base = self.atom()
        out = base[1]
        while self.peek() in ("_", "^"):
            op = self.take()
            out += f"{op}{{{_inner(self.atom())}}}"
            base = ("item", out)
        return base

    def atom(self) -> tuple[str, str]:
        t = self.take()
        if t == "{":
            items = self.seq({"}"})
            if self.peek() != "}":
                raise _Fail("unbalanced brace")
            self.take()
            return ("group", " ".join(x[1] for x in items))
        if t == "}":
            raise _Fail("unbalanced brace")
        if t.startswith('"'):
            return ("item", rf"\text{{{t[1:-1]}}}")
        if t in ("sqrt", "SQRT"):
            return ("item", rf"\sqrt{{{_inner(self.postfix())}}}")
        if t in ("root", "ROOT"):
            n = self.postfix()
            if self.peek() not in ("of", "OF"):
                raise _Fail("root without of")
            self.take()
            return ("item", rf"\sqrt[{_inner(n)}]{{{_inner(self.postfix())}}}")
        if t in ACCENTS:
            return ("item", f"{ACCENTS[t]}{{{_inner(self.atom())}}}")
        if t in MATRICES:
            return ("item", self.matrix(MATRICES[t]))
        if t in ("LEFT", "left", "RIGHT", "right"):
            d = self.take()
            d = {"{": r"\{", "}": r"\}"}.get(d, d)
            return ("item", (r"\left" if t.lower() == "left" else r"\right") + d)
        return ("item", _EXTRA.get(t) or SYMBOLS.get(t) or t)

    def matrix(self, env: str) -> str:
        if self.take() != "{":
            raise _Fail("matrix without brace")
        rows, cells, cur = [], [], []
        while True:
            t = self.peek()
            if t is None:
                raise _Fail("unbalanced matrix")
            if t in ("}", "#", "&"):
                self.take()
                cells.append(" ".join(cur))
                cur = []
                if t != "&":
                    rows.append(" & ".join(cells))
                    cells = []
                if t == "}":
                    break
            else:
                cur.append(self.postfix()[1])
        return rf"\begin{{{env}}}" + r" \\ ".join(rows) + rf"\end{{{env}}}"


def _inner(node: tuple[str, str]) -> str:
    return node[1]


def to_latex(script: str) -> str | None:
    p = _Parser(_tokens(script))
    try:
        items = p.seq(set())
    except _Fail:
        return None
    out = " ".join(x[1] if x[0] == "item" else "{" + x[1] + "}" for x in items)
    return out or None

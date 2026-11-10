import pytest
from helpers import FIX, blocks_of, para, para_raw, all_blocks, ctx_of, flat_text
from hwppipe.equation import to_latex

def norm(s): return "".join(s.split())
def paragraphs(path): return [x for x in all_blocks(path) if x["type"] == "paragraph"]

@pytest.mark.parametrize("src,latex", [
    ('{"123"} over {123 sqrt {3466}} sum _{34} ^{12}', r"\frac{\text{123}}{123\sqrt{3466}}\sum_{34}^{12}"),
    ("a over b", r"\frac{a}{b}"),
    ("alpha + beta", r"\alpha+\beta"),
    ("LEFT ( x RIGHT )", r"\left(x\right)"),
    ("x times y", r"x\timesy"),
    ("int _{0} ^{1} f(x) dx", r"\int_{0}^{1}f(x)dx"),
])
def test_to_latex(src, latex):
    assert norm(to_latex(src)) == norm(latex)

def test_unbalanced_returns_none():
    assert to_latex("{a over") is None


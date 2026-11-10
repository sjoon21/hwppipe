from helpers import FIX, blocks_of, para, para_raw, all_blocks, ctx_of, flat_text

def paragraphs(path): return [x for x in all_blocks(path) if x["type"] == "paragraph"]

def test_equation_inline_in_paragraph():
    p = paragraphs(FIX / "SimpleEquation.hwpx")
    eq = [e for x in p for e in x["equations"]][0]
    assert eq["script"] == '{"123"} over {123 sqrt {3466}} sum _{34} ^{12}'
    assert "$" + eq["latex"] + "$" in "".join(x["text"] for x in p)

def test_header_footer_separated():
    ctx = ctx_of(FIX / "HeaderFooter.hwpx")
    got = {(h["kind"], h["apply"], flat_text([h])) for h in ctx.headers_footers}
    assert got == {("header", "BOTH", "머리말 테스트"), ("footer", "BOTH", "꼬리말")}
    assert "머리말 테스트" not in flat_text(all_blocks(FIX / "HeaderFooter.hwpx"))

def test_footnote_and_endnote(tmp_path):
    inner = para_raw('<hp:t>본문</hp:t><hp:ctrl><hp:footNote><hp:subList>' + para("각주 내용") + '</hp:subList></hp:footNote></hp:ctrl>'
                     '<hp:ctrl><hp:endNote><hp:subList>' + para("미주 내용") + '</hp:subList></hp:endNote></hp:ctrl>')
    b, ctx = blocks_of(tmp_path, inner)
    assert b[0]["text"] == "본문[^fn-1][^en-1]"
    assert [(n["id"], flat_text([n])) for n in ctx.notes] == [("fn-1", "각주 내용"), ("en-1", "미주 내용")]

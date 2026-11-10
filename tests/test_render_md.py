import hashlib, json
from helpers import FIX, make_hwpx, read, para, para_raw, hpf, only_table, all_blocks
from hwppipe import convert
from hwppipe.render_md import table_html

PIC = '<hp:pic><hc:img binaryItemIDRef="{}"/></hp:pic>'
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16

def test_table_html_spans():
    html = table_html(only_table(all_blocks(FIX / "SimpleTable.hwpx")))
    assert '<td rowspan="2" colspan="2">1</td>' in html
    assert '<td colspan="2">4</td>' in html
    assert html.count("<tr>") == 3

def test_md_figure_and_comment(tmp_path):
    convert(FIX / "SimplePicture.hwpx", tmp_path)
    md = (tmp_path / "document.md").read_text(encoding="utf-8")
    assert "![fig-001](figures/image1.jpg)" in md

def test_md_table_anchor_comment(tmp_path):
    convert(FIX / "SimpleTable.hwpx", tmp_path)
    assert "<!-- table:tbl-001 -->" in (tmp_path / "document.md").read_text(encoding="utf-8")

def test_md_heading_and_list(tmp_path):
    convert(FIX / "ParaHead.hwpx", tmp_path)
    md = (tmp_path / "document.md").read_text(encoding="utf-8")
    assert "# 1. 개요1" in md and "## 가. 개요1-1" in md and "- 글머리1-1" in md

def test_md_equation_and_notes(tmp_path):
    inner = para_raw('<hp:t>식 </hp:t><hp:equation><hp:script>a over b</hp:script></hp:equation>'
                     '<hp:ctrl><hp:footNote><hp:subList>' + para("각주 내용") + '</hp:subList></hp:footNote></hp:ctrl>')
    convert(make_hwpx(tmp_path, inner), tmp_path / "o")
    md = (tmp_path / "o/document.md").read_text(encoding="utf-8")
    assert "식 $\\frac{a}{b}$[^fn-1]\n<!-- hwpeq: a over b -->" in md
    assert md.rstrip().endswith("[^fn-1]: 각주 내용")

def test_md_header_footer_label(tmp_path):
    convert(FIX / "HeaderFooter.hwpx", tmp_path)
    md = (tmp_path / "document.md").read_text(encoding="utf-8")
    assert "> [머리말 · 양쪽] 머리말 테스트" in md and "> [꼬리말 · 양쪽] 꼬리말" in md


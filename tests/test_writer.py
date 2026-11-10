import hashlib, json
from helpers import FIX, make_hwpx, read, para, para_raw, hpf, only_table, all_blocks
from hwppipe import convert
from hwppipe.render_md import table_html

PIC = '<hp:pic><hc:img binaryItemIDRef="{}"/></hp:pic>'
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16

def test_figures_bytes_identical(tmp_path):
    convert(FIX / "SimplePicture.hwpx", tmp_path)
    src = read(FIX / "SimplePicture.hwpx", "BinData/image1.jpg")
    assert (tmp_path / "figures/image1.jpg").read_bytes() == src
    m = json.loads((tmp_path / "figures.json").read_text(encoding="utf-8"))[0]
    assert m["sha256"] == hashlib.sha256(src).hexdigest() and m["referenced"] is True

def test_unreferenced_binary_saved(tmp_path):
    convert(make_hwpx(tmp_path, para("본문"), bins={"image1.png": PNG}), tmp_path / "o")
    m = json.loads((tmp_path / "o/figures.json").read_text(encoding="utf-8"))
    assert [(x["id"], x["file"], x["referenced"]) for x in m] == [(None, "figures/image1.png", False)]
    assert (tmp_path / "o/figures/image1.png").read_bytes() == PNG

def test_path_traversal_href(tmp_path):
    p = make_hwpx(tmp_path, para_raw(PIC.format("image1")), files={
        "Contents/content.hpf": hpf(["section0"], {"image1": "BinData/../../evil.png"}),
        "BinData/../../evil.png": PNG})
    convert(p, tmp_path / "out")
    assert not list(tmp_path.rglob("evil.png"))
    assert (tmp_path / "out/figures/image1.png").read_bytes() == PNG

def test_broken_section_is_partial(tmp_path):
    p = make_hwpx(tmp_path, para("살아남음"), files={
        "Contents/section1.xml": b"<broken", "Contents/content.hpf": hpf(["section0", "section1"])})
    r = convert(p, tmp_path / "o")
    assert r["status"] == "partial" and any("section1" in w for w in r["warnings"])
    assert "살아남음" in (tmp_path / "o/document.md").read_text(encoding="utf-8")

def test_skipped_writes_nothing(tmp_path):
    p = tmp_path / "a.hwpx"; p.write_bytes(b"\xD0\xCF\x11\xE0" + b"\0" * 100)
    r = convert(p, tmp_path / "out")
    assert r["status"] == "skipped" and r["skip_reason"] == "hwp5"
    assert not (tmp_path / "out").exists()

def test_deterministic(tmp_path):
    convert(FIX / "SimpleTable.hwpx", tmp_path / "a"); convert(FIX / "SimpleTable.hwpx", tmp_path / "b")
    for n in ["document.md", "document.json", "figures.json", "report.json"]:
        assert (tmp_path / "a" / n).read_bytes() == (tmp_path / "b" / n).read_bytes()

def test_json_has_no_private_keys(tmp_path):
    convert(FIX / "ParaHead.hwpx", tmp_path)
    assert '"_para_pr"' not in (tmp_path / "document.json").read_text(encoding="utf-8")

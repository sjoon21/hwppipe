import zipfile, pytest
from helpers import FIX, make_hwpx, hpf
from hwppipe import package
from hwppipe.package import open_hwpx, BinItem, Skipped, HwpxError
from hwppipe.xml import parse

def test_open_simple_picture_reads_manifest():
    pkg = open_hwpx(FIX / "SimplePicture.hwpx")
    assert pkg.sections == ["Contents/section0.xml"]
    assert pkg.bins["image1"] == BinItem("image1", "BinData/image1.jpg", "image/jpg", True)

def test_spine_order_not_filename_order(tmp_path):
    p = make_hwpx(tmp_path, "", files={
        "Contents/section1.xml": b'<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"/>',
        "Contents/content.hpf": hpf(["section1", "section0"])})
    assert open_hwpx(p).sections == ["Contents/section1.xml", "Contents/section0.xml"]

def test_metadata_creator():
    assert open_hwpx(FIX / "SimpleTable.hwpx").metadata["creator"] == "fff"

@pytest.mark.parametrize("head,reason", [
    (b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1", "hwp5"),
    (b"hello", "not_zip"),
])
def test_skip_non_hwpx(tmp_path, head, reason):
    p = tmp_path / "x.hwpx"; p.write_bytes(head + b"\0" * 100)
    with pytest.raises(Skipped) as e:
        open_hwpx(p)
    assert e.value.reason == reason

def test_skip_zip_with_wrong_mimetype(tmp_path):
    p = tmp_path / "x.hwpx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")   # docx 같은 일반 ZIP
    with pytest.raises(Skipped) as e:
        open_hwpx(p)
    assert e.value.reason == "not_hwpx"

def test_skip_encrypted(tmp_path):
    p = make_hwpx(tmp_path, "", files={"META-INF/manifest.xml":
        b'<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
        b'<odf:file-entry odf:full-path="Contents/section0.xml"><odf:encryption-data/></odf:file-entry></odf:manifest>'})
    with pytest.raises(Skipped) as e:
        open_hwpx(p)
    assert e.value.reason == "encrypted"

def test_missing_manifest_xml_is_ok(tmp_path):
    p = make_hwpx(tmp_path, "", files={"META-INF/manifest.xml": None})
    assert open_hwpx(p).sections == ["Contents/section0.xml"]

def test_xml_entities_not_resolved():
    root = parse(b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>')
    assert "root:" not in (root.text or "")

def test_entry_over_limit_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "MAX_ENTRY_UNCOMPRESSED", 1000)
    p = make_hwpx(tmp_path, "", files={"BinData/big.bin": b"\0" * 1001})
    with pytest.raises(HwpxError):
        open_hwpx(p).read("BinData/big.bin")

def test_too_many_entries_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "MAX_ENTRIES", 5)
    p = make_hwpx(tmp_path, "", files={f"BinData/{i}.bin": b"x" for i in range(10)})
    with pytest.raises(HwpxError):
        open_hwpx(p)

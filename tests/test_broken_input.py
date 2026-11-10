"""손상된 패키지 파일: 처리되지 않은 예외 대신 partial(내용 유지) 또는 skipped(사유 기록)."""
import pytest
from helpers import HEADER_XML, make_hwpx, para

from hwppipe import convert, parse
from hwppipe.package import Skipped


@pytest.mark.parametrize("header", [b"<hh:head", None, HEADER_XML.replace(b'level="1"', b'level="x"', 1)],
                         ids=["xml_error", "missing", "bad_number"])
def test_broken_header_keeps_text(tmp_path, header):
    src = make_hwpx(tmp_path, para("본문 글"), files={"Contents/header.xml": header})
    r = convert(src, tmp_path / "o")
    assert r["status"] == "partial" and any("header.xml" in w for w in r["warnings"])
    assert "본문 글" in (tmp_path / "o/document.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["Contents/content.hpf", "META-INF/manifest.xml"])
def test_broken_package_file_is_skipped(tmp_path, name):
    src = make_hwpx(tmp_path, para("x"), files={name: b"<broken"})
    r = convert(src, tmp_path / "o")
    assert (r["status"], r["skip_reason"]) == ("skipped", "broken_package")
    with pytest.raises(Skipped):
        parse(src)

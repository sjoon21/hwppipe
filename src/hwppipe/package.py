"""HWPX ZIP 패키지 열기: 입력 판별, manifest·spine·metadata, 안전한 엔트리 읽기."""
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from .xml import NS, parse, q

MAX_ENTRIES = 10_000
MAX_ENTRY_UNCOMPRESSED = 256_000_000
MAX_TOTAL_UNCOMPRESSED = 1_000_000_000

_SECTION_RE = re.compile(r"Contents/section(\d+)\.xml$")


class HwpxError(Exception):
    pass


class Skipped(HwpxError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class BinItem:
    id: str
    href: str
    media_type: str
    embedded: bool


@dataclass
class Package:
    path: Path
    sections: list[str]
    bins: dict[str, BinItem]
    metadata: dict[str, str]
    _zf: zipfile.ZipFile = field(repr=False, default=None)
    _read_total: int = field(repr=False, default=0)

    def read(self, name: str) -> bytes:
        # ZIP 헤더의 크기는 위조될 수 있으므로 실제로 읽은 양으로 한도를 검사한다
        with self._zf.open(name) as f:
            data = f.read(MAX_ENTRY_UNCOMPRESSED + 1)
        if len(data) > MAX_ENTRY_UNCOMPRESSED:
            raise HwpxError(f"entry too large: {name}")
        self._read_total += len(data)
        if self._read_total > MAX_TOTAL_UNCOMPRESSED:
            raise HwpxError("total uncompressed size over limit")
        return data

    def close(self) -> None:
        self._zf.close()

    def has(self, name: str) -> bool:
        try:
            self._zf.getinfo(name)
            return True
        except KeyError:
            return False


def open_hwpx(path: Path) -> Package:
    path = Path(path)
    with open(path, "rb") as f:
        head = f.read(8)
    if head[:4] != b"PK\x03\x04":
        raise Skipped("hwp5" if head[:4] == b"\xD0\xCF\x11\xE0" else "not_zip")
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise Skipped("not_zip")
    try:
        infos = zf.infolist()
        if len(infos) > MAX_ENTRIES:
            raise HwpxError("too many entries")
        if sum(i.file_size for i in infos) > MAX_TOTAL_UNCOMPRESSED:
            raise HwpxError("total uncompressed size over limit")
        pkg = Package(path, [], {}, {}, zf)
        if not pkg.has("mimetype") or pkg.read("mimetype").strip() != b"application/hwp+zip":
            raise Skipped("not_hwpx")
        try:
            if pkg.has("META-INF/manifest.xml"):
                if parse(pkg.read("META-INF/manifest.xml")).find(".//" + q("odf", "encryption-data")) is not None:
                    raise Skipped("encrypted")
            _read_content(pkg)
        except etree.XMLSyntaxError:
            raise Skipped("broken_package")  # 구역 목록·암호 여부를 알 수 없으면 본문을 읽을 수 없다
    except BaseException:
        zf.close()
        raise
    return pkg


def _read_content(pkg: Package) -> None:
    if not pkg.has("Contents/content.hpf"):
        raise Skipped("not_hwpx")
    root = parse(pkg.read("Contents/content.hpf"))
    hrefs: dict[str, str] = {}
    for item in root.iterfind(f".//{q('opf', 'manifest')}/{q('opf', 'item')}"):
        iid, href = item.get("id", ""), item.get("href", "")
        hrefs[iid] = href
        if href.startswith("BinData/") or item.get("isEmbeded") is not None:
            pkg.bins[iid] = BinItem(iid, href, item.get("media-type", ""), item.get("isEmbeded", "1") != "0")
    spine = [hrefs.get(r.get("idref", ""), "") for r in root.iterfind(f".//{q('opf', 'spine')}/{q('opf', 'itemref')}")]
    sections = [h for h in spine if _SECTION_RE.search(h)]
    if not sections:
        sections = sorted((h for h in hrefs.values() if _SECTION_RE.search(h)),
                          key=lambda h: int(_SECTION_RE.search(h).group(1)))
    pkg.sections = sections
    md = root.find(q("opf", "metadata"))
    if md is not None:
        title = md.findtext(q("opf", "title"))
        if title:
            pkg.metadata["title"] = title
        for m in md.iterfind(q("opf", "meta")):
            if m.get("name") and m.text:
                pkg.metadata[m.get("name")] = m.text

"""테스트 헬퍼: 합성 HWPX 생성과 픽스처 접근."""
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

FIX = Path(__file__).parent / "fixtures/hwpxlib"


def read(path: Path, name: str) -> bytes:
    with zipfile.ZipFile(path) as z:
        return z.read(name)


_SEC0 = read(FIX / "SimpleTable.hwpx", "Contents/section0.xml").decode("utf-8")
SEC_OPEN = re.search(r"<hs:sec\b[^>]*>", _SEC0).group(0)
HEADER_XML = read(FIX / "SimpleTable.hwpx", "Contents/header.xml")

_HPF_NS = (
    'xmlns:opf="http://www.idpf.org/2007/opf/" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/"'
)
_MEDIA = {"png": "image/png", "jpg": "image/jpg", "jpeg": "image/jpeg", "bmp": "image/bmp", "gif": "image/gif"}


def hpf(sections: list[str], bins: dict[str, str] | None = None) -> bytes:
    items = ['<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>']
    for s in sections:
        items.append(f'<opf:item id="{s}" href="Contents/{s}.xml" media-type="application/xml"/>')
    for bid, href in (bins or {}).items():
        ext = href.rsplit(".", 1)[-1].lower()
        items.append(
            f'<opf:item id="{escape(bid)}" href="{escape(href)}" '
            f'media-type="{_MEDIA.get(ext, "application/octet-stream")}" isEmbeded="1"/>'
        )
    spine = "".join(f'<opf:itemref idref="{s}" linear="yes"/>' for s in ["header", *sections])
    return (
        f'<?xml version="1.0" encoding="UTF-8"?><opf:package {_HPF_NS} version="" unique-identifier="" id="">'
        f'<opf:metadata><opf:title/><opf:language>ko</opf:language></opf:metadata>'
        f'<opf:manifest>{"".join(items)}</opf:manifest><opf:spine>{spine}</opf:spine></opf:package>'
    ).encode("utf-8")


_CONTAINER = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
    b'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf"><ocf:rootfiles>'
    b'<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
    b"</ocf:rootfiles></ocf:container>"
)
_MANIFEST = b'<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>'


def make_hwpx(
    tmp_path: Path,
    section_xml: str,
    header_xml: bytes | None = None,
    bins: dict[str, bytes] | None = None,
    files: dict[str, bytes | None] | None = None,
    name: str = "t.hwpx",
) -> Path:
    bins = bins or {}
    entries: dict[str, bytes | None] = {
        "META-INF/container.xml": _CONTAINER,
        "META-INF/manifest.xml": _MANIFEST,
        "Contents/content.hpf": hpf(["section0"], {n.rsplit(".", 1)[0]: f"BinData/{n}" for n in bins}),
        "Contents/header.xml": header_xml or HEADER_XML,
        "Contents/section0.xml": (SEC_OPEN + section_xml + "</hs:sec>").encode("utf-8"),
    }
    for n, data in bins.items():
        entries[f"BinData/{n}"] = data
    entries.update(files or {})
    p = tmp_path / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        for n, data in entries.items():
            if data is not None:
                z.writestr(n, data)
    return p


def para(text: str, para_pr: str = "0") -> str:
    return para_raw(f"<hp:t>{escape(text)}</hp:t>", para_pr)


def para_raw(run_inner: str, para_pr: str = "0") -> str:
    return f'<hp:p paraPrIDRef="{para_pr}"><hp:run charPrIDRef="0">{run_inner}</hp:run></hp:p>'


def tbl_xml(
    rows: int,
    cols: int,
    cells: list[tuple[int, int, int, int, str]],
    caption: str | None = None,
    side: str = "TOP",
    header_cells: set[tuple[int, int]] = frozenset(),
    border_fill: str | None = None,
) -> str:
    cap = ""
    if caption is not None:
        cap = f'<hp:caption side="{side}"><hp:subList>{para(caption)}</hp:subList></hp:caption>'
    trs = []
    for r in sorted({c[0] for c in cells}):
        tcs = []
        for row, col, rs, cs, inner in cells:
            if row != r:
                continue
            hdr = "1" if (row, col) in header_cells else "0"
            bf = f' borderFillIDRef="{border_fill}"' if border_fill else ""
            tcs.append(
                f'<hp:tc header="{hdr}"{bf}><hp:subList>{inner}</hp:subList>'
                f'<hp:cellAddr colAddr="{col}" rowAddr="{row}"/><hp:cellSpan colSpan="{cs}" rowSpan="{rs}"/></hp:tc>'
            )
        trs.append("<hp:tr>" + "".join(tcs) + "</hp:tr>")
    return f'<hp:tbl rowCnt="{rows}" colCnt="{cols}">{cap}{"".join(trs)}</hp:tbl>'


# --- Task 3: 본문 순회 헬퍼 ---
def _ctx_for(pkg):
    from hwppipe.body import Ctx
    from hwppipe.header import parse_header
    return Ctx(pkg, parse_header(pkg.read("Contents/header.xml")))


def blocks_of(tmp_path, inner: str, header: bytes | None = None):
    from hwppipe.body import parse_section
    from hwppipe.package import open_hwpx
    pkg = open_hwpx(make_hwpx(tmp_path, inner, header))
    ctx = _ctx_for(pkg)
    return parse_section(pkg.read(pkg.sections[0]), 0, ctx)[0], ctx


def _sections(path: Path):
    from hwppipe.body import parse_section
    from hwppipe.package import open_hwpx
    pkg = open_hwpx(path)
    ctx = _ctx_for(pkg)
    secs = [parse_section(pkg.read(s), i, ctx) for i, s in enumerate(pkg.sections)]
    return secs, ctx


def all_blocks(path: Path) -> list[dict]:
    return [b for blocks, _ in _sections(path)[0] for b in blocks]


def ctx_of(path: Path):
    return _sections(path)[1]


def iter_blocks(blocks):
    for b in blocks:
        yield b
        for c in b.get("cells", []):
            yield from iter_blocks(c["blocks"])
        yield from iter_blocks(b.get("blocks", []))


def flat_text(blocks) -> str:
    return "\n".join(b["text"] for b in iter_blocks(blocks) if "text" in b)


# --- Task 4 ---
def only_table(path_or_blocks) -> dict:
    blocks = all_blocks(path_or_blocks) if isinstance(path_or_blocks, Path) else path_or_blocks
    tables = [b for b in blocks if b["type"] == "table"]
    assert len(tables) == 1, f"expected 1 table, got {len(tables)}"
    return tables[0]


# --- Task 5 ---
def figures(path: Path) -> list[dict]:
    return [b for b in iter_blocks(all_blocks(path)) if b["type"] == "figure"]


# --- Task 7 ---
def assigned(path: Path) -> list[dict]:
    from hwppipe.headings import assign
    secs, ctx = _sections(path)
    return assign(secs, ctx.header)


def assert_heading_chain(doc):
    """그래프에서 블록의 Heading 조상을 거슬러 올라간 경로가 heading_path와 같아야 한다."""
    from hwppipe import to_graph
    g = to_graph(doc)
    nodes = {n["id"]: n for n in g["nodes"]}
    parent = {e["target"]: e["source"] for e in g["edges"] if e["type"] == "CONTAINS"}
    label = lambda n: f"{n['prefix']} {n['text']}" if n.get("prefix") else n["text"]  # noqa: E731
    for b in doc["blocks"]:
        if "id" not in b:
            continue
        chain, cur = [], b["id"]
        if nodes[cur]["type"] == "Heading":
            chain.append(label(nodes[cur]))
        while cur in parent:
            cur = parent[cur]
            if nodes[cur]["type"] == "Heading":
                chain.append(label(nodes[cur]))
        assert chain[::-1] == b["heading_path"], b["id"]

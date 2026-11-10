"""안전한 XML 파싱과 HWPX 네임스페이스."""
from collections.abc import Iterator

from lxml import etree

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "opf": "http://www.idpf.org/2007/opf/",
    "odf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
}


def _parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


def parse(data: bytes) -> etree._Element:
    return etree.fromstring(data, _parser())


def q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def local(el) -> str:
    """요소의 local name. 주석·처리 명령은 빈 문자열."""
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


_SWITCH = q("hp", "switch")
_DEFAULT = q("hp", "default")


def children(el) -> Iterator[etree._Element]:
    """자식 요소를 내보낸다. hp:switch는 hp:default 갈래만 펼친다(case와 내용이 중복되므로)."""
    for c in el:
        if not isinstance(c.tag, str):
            continue
        if c.tag == _SWITCH:
            for d in c:
                if d.tag == _DEFAULT:
                    yield from children(d)
        else:
            yield c

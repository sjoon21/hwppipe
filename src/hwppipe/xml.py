"""안전한 XML 파싱과 HWPX 네임스페이스."""
import re
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


# XML 1.0이 허용하지 않는 제어 문자. 한글이 가끔 그대로 저장해 구역 전체를 읽지 못하게 만든다.
# UTF-8에서 0x00~0x1F 바이트는 여러 바이트 문자 안에 나타나지 않으므로 바이트 단위로 고쳐도 안전하다.
_CTRL = re.compile(rb"[\x01-\x08\x0e-\x1f]")
_BREAK = re.compile(rb"[\x0b\x0c]")  # 세로 탭·쪽 넘김(Word에서 붙여 넣은 줄바꿈)은 줄바꿈으로 바꾼다


def parse_counted(data: bytes) -> tuple[etree._Element, int]:
    """XML을 파싱한다. 금지된 제어 문자 때문에 실패하면 고쳐서 다시 파싱하고, 고친 글자 수를 함께 돌려준다."""
    try:
        return etree.fromstring(data, _parser()), 0
    except etree.XMLSyntaxError as e:
        n = len(_CTRL.findall(data)) + len(_BREAK.findall(data))
        if not n or b"\x00" in data:  # UTF-16처럼 0 바이트가 있는 인코딩은 바이트 단위로 고칠 수 없다
            raise
        try:
            return etree.fromstring(_BREAK.sub(b"\n", _CTRL.sub(b"", data)), _parser()), n
        except etree.XMLSyntaxError:
            raise e from None  # 고쳐도 실패하면 원래 오류를 알린다


def parse(data: bytes) -> etree._Element:
    return parse_counted(data)[0]


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

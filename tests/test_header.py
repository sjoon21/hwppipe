import pytest
from helpers import FIX, read
from hwppipe.header import parse_header
from hwppipe.numbering import format_number, Numberer

@pytest.fixture
def h():
    return parse_header(read(FIX / "ParaHead.hwpx", "Contents/header.xml"))

def test_parse_header_parahead(h):
    assert h.para_heading["19"] == ("OUTLINE", "0", 0)
    assert h.para_heading["24"] == ("NUMBER", "3", 0)
    assert h.para_heading["16"] == ("BULLET", "1", 0)
    assert h.numberings["1"][2] == ("HANGUL_SYLLABLE", "^2.", 1)
    assert h.numberings["3"][2][1] == "^1.^2."

def test_numberer_parahead_sequence(h):
    # ParaHead.hwpx 본문 순서의 (paraPrIDRef) 목록을 넣고 번호를 확인한다
    seq = ["24","24","24","25","25","26","27","27","28","27","19","20","20","20","19","20","21"]
    n = Numberer(h, outline_id="1")
    got = [n.prefix(p)[2] for p in seq]
    assert got == ["1.","2.","3.","3.1.","3.2.","4.","4.1.1.1.","4.1.1.2.","4.1.2.","4.1.2.1.",
                   "1.","가.","나.","다.","2.","가.","1)"]

def test_bullet_prefix_is_dash(h):
    assert Numberer(h, "1").prefix("16") == ("BULLET", 0, "-")

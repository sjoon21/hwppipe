import pytest
from helpers import FIX, read
from hwppipe.header import parse_header
from hwppipe.numbering import format_number, Numberer

@pytest.fixture
def h():
    return parse_header(read(FIX / "ParaHead.hwpx", "Contents/header.xml"))

def test_format_number():
    assert format_number(3, "DIGIT") == "3"
    assert format_number(2, "HANGUL_SYLLABLE") == "나"
    assert format_number(14, "HANGUL_SYLLABLE") == "하"
    assert format_number(1, "CIRCLED_DIGIT") == "①"
    assert format_number(4, "ROMAN_CAPITAL") == "IV"
    assert format_number(3, "LATIN_SMALL") == "c"
    assert format_number(5, "UNKNOWN_FMT") == "5"   # 모르는 형식은 DIGIT
    assert format_number(15, "HANGUL_SYLLABLE") == "15"   # 표현 범위를 넘으면 숫자
    assert format_number(21, "CIRCLED_DIGIT") == "21"


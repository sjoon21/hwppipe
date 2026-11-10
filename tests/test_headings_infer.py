from hwppipe.header import Header
from hwppipe.headings import infer

HDR = Header(para_heading={}, numberings={}, bullets={}, char_props={"0": (1000, False), "2": (1400, True)})

def P(text, char_pr="0"): return {"type": "paragraph", "text": text, "equations": [], "_para_pr": "0", "_char_pr": char_pr, "loc": {}}

def test_public_doc_hierarchy():
    b = [P("Ⅰ. 추진 배경"), P("1. 현황"), P("가. 기상 특보"), P("본문 문장입니다."),
         P("나. 피해 현황"), P("2. 문제점"), P("Ⅱ. 추진 계획")]
    infer(b, HDR)
    assert [(x.get("prefix"), x.get("level")) for x in b if x["type"] == "heading"] == \
           [("Ⅰ.",1),("1.",2),("가.",3),("나.",3),("2.",2),("Ⅱ.",1)]
    assert b[0]["text"] == "추진 배경" and b[0]["heading_source"] == "inferred"

def test_levels_follow_canonical_order_not_first_appearance():
    # 첫 쪽에 "가." 형식의 안내 문구가 먼저 나와도 위계는 표준 순서(1. > 가. > (1))를 따른다
    b = [P("가. 참고 사항"), P("1. 개요"), P("가. 목적"), P("(1) 세부")]
    infer(b, HDR)
    assert [x["level"] for x in b] == [2, 1, 2, 3]

def test_hangul_pattern_only_first_14_syllables():
    b = [P("1. 개요"), P("각. 이것은 제목이 아니다")]
    infer(b, HDR)
    assert b[1]["type"] == "paragraph" and b[1]["text"] == "각. 이것은 제목이 아니다"

def test_sentence_like_numbered_paragraph_is_list_item():
    b = [P("1. 개요"), P("2. 본 사업은 재난 대응 체계를 개선하기 위하여 2015년부터 추진하였다.")]
    infer(b, HDR)
    assert b[1]["type"] == "list_item" and b[1]["prefix"] == "2."
    assert b[1]["text"].startswith("본 사업은")

def test_long_paragraph_not_heading():
    b = [P("1. 개요"), P("가. " + "나" * 80)]
    infer(b, HDR)
    assert b[1]["type"] == "list_item"

def test_large_text_without_number_when_no_numbered_headings():
    b = [P("추진 배경", "2"), P("본문 문장입니다."), P("두 번째 본문 문장입니다.")]
    infer(b, HDR)
    assert (b[0]["type"], b[0]["level"], b[0]["prefix"]) == ("heading", 1, None)

def test_large_text_ranks_above_numbered_headings():
    # 실문서(평가 계획서)는 번호 제목 위에 번호 없는 큰 제목을 둔다
    b = [P("1. 개요"), P("강조 문구", "2")]
    infer(b, HDR)
    assert [(x["type"], x["level"]) for x in b] == [("heading", 2), ("heading", 1)]


def test_leading_spaces_before_number():
    # 실문서는 공백 문자로 들여쓰기를 한다: " 1. 행사개요", "   가. 행사운영 분야"
    b = [P(" 1. 행사개요"), P("   가. 행사운영 분야")]
    infer(b, HDR)
    assert [(x["type"], x["prefix"], x["text"], x["level"]) for x in b] == \
           [("heading", "1.", "행사개요", 1), ("heading", "가.", "행사운영 분야", 2)]


HDR2 = Header(char_props={"0": (1300, False), "b": (1300, True), "big": (1600, False), "title": (2100, False)})


def test_emphasis_required_when_doc_emphasizes_numbered_headings():
    b = [P("1. 행사개요", "big"), P("가. 행사운영 분야", "b"), P("1) 문화행사"), P("2) 공식행사")]
    infer(b, HDR2)
    assert [x["type"] for x in b] == ["heading", "heading", "list_item", "list_item"]


def test_label_value_is_not_heading():
    b = [P("1. 행사개요", "big"), P("가. 행사장소: 국립4·19민주묘지", "b")]
    infer(b, HDR2)
    assert b[1]["type"] == "list_item"


def test_large_unnumbered_titles_rank_above_numbered():
    b = [P("평가 계획", "title"), P("가. 기본 방향"), P("1) 물질의 상태"), P("본문 문장입니다.")]
    infer(b, HDR2)
    assert [(x["type"], x.get("level")) for x in b] == \
           [("heading", 1), ("heading", 2), ("heading", 3), ("paragraph", None)]


def test_slightly_larger_text_is_not_emphasis():
    # 본문 11pt에 12pt 문단 하나가 섞여도 번호 제목 판정 기준이 바뀌지 않아야 한다
    hdr = Header(char_props={"0": (1100, False), "s": (1200, False)})
    b = [P("가. 기본 방향"), P("1) 화학의 핵심 개념을 이해하고 적용하는 능력을 평가한다."),
         P("2) 반응 엔탈피와 화학 평형", "s"), P("나. 방침")]
    infer(b, hdr)
    assert [x["type"] for x in b] == ["heading", "list_item", "heading", "heading"]


def test_bullet_symbol_lines_are_not_large_titles():
    hdr = Header(char_props={"0": (1100, False), "m": (1400, False), "t": (2100, False)})
    b = [P("■ 3월", "m"), P("※ 참고", "m"), P("평가 계획", "t"), P("본문 문장입니다. 길게 쓴 본문입니다.")]
    infer(b, hdr)
    assert [x["type"] for x in b] == ["paragraph", "paragraph", "heading", "paragraph"]


HDR3 = Header(char_props={"0": (1300, False), "b": (1300, True), "ch": (1600, False), "chb": (1600, True),
                          "t1": (3500, False), "t2": (2800, False), "t3": (2200, True), "m": (1400, False),
                          "h18": (1800, False), "h16": (1600, True), "h15": (1500, True)})
BODY = "본문 문장이 이어집니다. 충분히 긴 본문 문장입니다"


def test_number_dominant_doc_title_on_top_and_cover_lines_level_with_chapters():
    b = [P("2023. 7. 5.", "t3"), P("『제2회 음악축제』", "t1"), P("행사대행 제안요청서", "t2"),
         P("1. 행사개요", "ch"), P("가. 운영 분야", "b"), P(BODY), P("2. 과업개요", "ch"), P("가. 과업범위", "b"),
         P(BODY), P("나. 과업기간", "b"), P("【서식 1】", "chb"), P(BODY)]
    infer(b, HDR3)
    lv = {x["text"]: x["level"] for x in b if x["type"] == "heading"}
    assert lv["『제2회 음악축제』"] == 1
    assert (lv["행사개요"], lv["운영 분야"]) == (2, 3)
    assert lv["【서식 1】"] == 2 and lv["행사대행 제안요청서"] == 2


def test_number_dominant_minor_large_line_does_not_push_levels():
    hdr = Header(char_props={"0": (1100, False), "m": (1400, False), "t": (2100, False)})
    b = [P("평가 계획", "t"), P("담당교사 홍길동", "m"), P("가. 기본 방향"), P("1) 물질의 상태"),
         P("나. 방침"), P("2) 반응과 평형"), P(BODY)]
    infer(b, hdr)
    lv = [(x["text"], x["level"]) for x in b if x["type"] == "heading"]
    assert lv == [("평가 계획", 1), ("담당교사 홍길동", 2), ("기본 방향", 2), ("물질의 상태", 3),
                  ("방침", 2), ("반응과 평형", 3)]


def test_size_dominant_keeps_size_tiers_above_numbers():
    b = [P("기상전망", "h18"), P("날씨 전망", "h16"), P(BODY), P("기온", "h16"), P(BODY),
         P("자연재난", "h18"), P("분석", "h16"), P("가. 대설", "h15"), P(BODY)]
    infer(b, HDR3)
    lv = [(x["text"], x["level"]) for x in b if x["type"] == "heading"]
    assert lv == [("기상전망", 1), ("날씨 전망", 2), ("기온", 2), ("자연재난", 1), ("분석", 2), ("대설", 3)]

"""최종 리뷰에서 나온 결함의 회귀 테스트."""
import json
import shutil

import pytest
from helpers import FIX, ctx_of, make_hwpx, para, para_raw, tbl_xml

from hwppipe import convert
from hwppipe.cli import main


def _md(p):
    return (p / "document.md").read_text(encoding="utf-8")


# 1. 출력 단계가 사용자 데이터를 지우면 안 된다
def test_refuses_to_replace_foreign_folder(tmp_path):
    out = tmp_path / "report"
    out.mkdir()
    (out / "notes.txt").write_text("내 메모", encoding="utf-8")
    with pytest.raises(FileExistsError):
        convert(FIX / "SimpleTable.hwpx", out)
    assert (out / "notes.txt").read_text(encoding="utf-8") == "내 메모"


def test_rerun_replaces_previous_output(tmp_path):
    convert(FIX / "SimpleTable.hwpx", tmp_path / "o")
    (tmp_path / "o/document.md").write_text("변조", encoding="utf-8")
    convert(FIX / "SimpleTable.hwpx", tmp_path / "o")
    assert _md(tmp_path / "o") != "변조"


def test_cli_refuses_output_inside_input(tmp_path):
    src = tmp_path / "docs"
    (src / "foo").mkdir(parents=True)
    shutil.copy(FIX / "SimpleTable.hwpx", src / "foo.hwpx")
    (src / "foo/notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit):
        main([str(src), "-o", str(src)])
    assert (src / "foo/notes.txt").exists()


def test_cli_output_prefix_collision(tmp_path):
    src = tmp_path / "in"
    (src / "A").mkdir(parents=True)
    shutil.copy(FIX / "SimpleTable.hwpx", src / "A/b.hwpx")
    shutil.copy(FIX / "SimpleTable.hwpx", src / "a.hwpx")
    main([str(src), "-o", str(tmp_path / "out")])
    s = json.loads((tmp_path / "out/report.json").read_text(encoding="utf-8"))
    assert [(d["output"], d["status"]) for d in s["documents"]] == [("A/b", "ok"), ("a~2", "ok")]
    assert (tmp_path / "out/A/b/document.md").exists()


# 2. 개체 하나가 깨져도 구역 전체를 버리지 않는다
def test_broken_table_is_a_loss_not_a_lost_section(tmp_path):
    bad = '<hp:tbl rowCnt="1" colCnt="1"><hp:tr><hp:tc><hp:subList>' + para("셀") + \
          '</hp:subList></hp:tc></hp:tr></hp:tbl>'  # cellAddr 없음
    r = convert(make_hwpx(tmp_path, para("앞") + para_raw(bad) + para("뒤")), tmp_path / "o")
    md = _md(tmp_path / "o")
    assert r["status"] == "ok" and "앞" in md and "뒤" in md
    assert any(x["kind"] == "broken_tbl" for x in r["losses"])
    lost = sum(x["chars"] for x in r["losses"])
    assert r["counts"]["chars_source"] == r["counts"]["chars_emitted"] + lost


# 3. 짝이 없는 deleteBegin이 나머지 문서를 지우면 안 된다
def test_unmatched_delete_begin_does_not_swallow_document(tmp_path):
    inner = para_raw('<hp:t>남김<hp:deleteBegin Id="9"/>삭제?</hp:t>') + para("다음 문단")
    r = convert(make_hwpx(tmp_path, inner), tmp_path / "o")
    assert "다음 문단" in _md(tmp_path / "o")
    assert any("deleteBegin" in w for w in r["warnings"])


# 4. 글상자·각주 안의 표와 그림, 행 수가 틀린 표, 숨은 설명도 출력에 남는다
def test_table_inside_textbox_is_rendered(tmp_path):
    box = ('<hp:rect><hp:drawText><hp:subList>' + para("상자 글") +
           para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("상자 속 표"))])) + '</hp:subList></hp:drawText></hp:rect>')
    convert(make_hwpx(tmp_path, para_raw(box)), tmp_path / "o")
    assert "상자 속 표" in _md(tmp_path / "o")


def test_table_inside_footnote_is_rendered(tmp_path):
    fn = ('<hp:t>본문</hp:t><hp:ctrl><hp:footNote><hp:subList>' +
          para_raw(tbl_xml(1, 1, [(0, 0, 1, 1, para("각주 속 표"))])) + '</hp:subList></hp:footNote></hp:ctrl>')
    convert(make_hwpx(tmp_path, para_raw(fn)), tmp_path / "o")
    assert "각주 속 표" in _md(tmp_path / "o")


def test_table_with_too_small_rowcnt_keeps_cells(tmp_path):
    t = tbl_xml(1, 1, [(0, 0, 1, 1, para("첫 행")), (1, 0, 1, 1, para("넘친 행"))])
    convert(make_hwpx(tmp_path, para_raw(t)), tmp_path / "o")
    assert "넘친 행" in _md(tmp_path / "o")


def test_hidden_comment_kept_in_outputs(tmp_path):
    inner = para_raw('<hp:t>본문</hp:t><hp:ctrl><hp:hiddenComment><hp:subList>' + para("숨은 설명 내용") +
                     '</hp:subList></hp:hiddenComment></hp:ctrl>')
    convert(make_hwpx(tmp_path, inner), tmp_path / "o")
    dj = json.loads((tmp_path / "o/document.json").read_text(encoding="utf-8"))
    assert dj["hidden_comments"][0]["text"] == "숨은 설명 내용"
    assert "> [숨은 설명] 숨은 설명 내용" in _md(tmp_path / "o")


# 5. manifest에는 있지만 ZIP에 데이터가 없는 그림은 손실로 기록한다
def test_missing_binary_data_is_a_loss(tmp_path):
    from helpers import hpf
    p = make_hwpx(tmp_path, para_raw('<hp:pic><hc:img binaryItemIDRef="image1"/></hp:pic>'),
                  files={"Contents/content.hpf": hpf(["section0"], {"image1": "BinData/image1.png"})})
    r = convert(p, tmp_path / "o")
    assert any(x["kind"] == "missing_binary_data" for x in r["losses"])


# 6. 묶음 개체의 크기·위치 속성 요소는 손실이 아니다
def test_container_properties_are_not_losses():
    assert ctx_of(FIX / "SimpleContainer.hwpx").losses == {}


# 8. 대소문자만 다른 그림 파일이 서로 덮어쓰면 안 된다
def test_case_only_different_image_names(tmp_path):
    from helpers import hpf
    p = make_hwpx(tmp_path, para("x"), files={
        "Contents/content.hpf": hpf(["section0"], {"i1": "BinData/A.png", "i2": "BinData/a.png"}),
        "BinData/A.png": b"\x89PNG-upper", "BinData/a.png": b"\x89PNG-lower"})
    convert(p, tmp_path / "o")
    figs = json.loads((tmp_path / "o/figures.json").read_text(encoding="utf-8"))
    files = [f["file"] for f in figs]
    assert len({f.lower() for f in files}) == 2
    for f in figs:
        assert (tmp_path / "o" / f["file"]).read_bytes() in (b"\x89PNG-upper", b"\x89PNG-lower")
    assert {(tmp_path / "o" / f["file"]).read_bytes() for f in figs} == {b"\x89PNG-upper", b"\x89PNG-lower"}

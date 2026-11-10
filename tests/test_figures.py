from helpers import FIX, make_hwpx, para_raw, all_blocks, ctx_of, figures, flat_text, hpf

PIC = '<hp:pic><hc:img binaryItemIDRef="{}"/></hp:pic>'

def test_simple_picture():
    f = figures(FIX / "SimplePicture.hwpx")
    assert len(f) == 1
    assert f[0]["binary_id"] == "image1"
    assert f[0]["original_name"] == "google.jpg"
    assert f[0]["pixel_size"] == [544, 184]
    assert f[0]["id"] == "fig-001"

def test_pictures_inside_container_found():
    assert [x["binary_id"] for x in figures(FIX / "SimpleContainer.hwpx")] == ["image1", "image2"]

def test_textbox_text_kept():
    b = all_blocks(FIX / "RectInRect.hwpx")
    boxes = [x for x in b if x["type"] == "textbox"]
    assert "사각형 안에 사각형의 텍스트입니다." in flat_text(boxes)

def test_figure_with_missing_binary(tmp_path):
    p = make_hwpx(tmp_path, para_raw(PIC.format("nope")))
    assert figures(p)[0]["binary_id"] == "nope"
    assert "missing_binary" in ctx_of(p).losses

def test_link_picture_recorded(tmp_path):
    p = make_hwpx(tmp_path, para_raw(PIC.format("image1")),
                  files={"Contents/content.hpf": hpf(["section0"], {"image1": "C:/외부/a.png"}).replace(
                      b'isEmbeded="1"', b'isEmbeded="0"')})
    assert "link_picture" in ctx_of(p).losses

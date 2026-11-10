from helpers import FIX, blocks_of, all_blocks, ctx_of, flat_text, para_raw

def lost_chars(ctx): return sum(x["chars"] for v in ctx.losses.values() for x in v)

def test_mixed_content_tab_linebreak(tmp_path):
    b, _ = blocks_of(tmp_path, '<hp:p paraPrIDRef="0"><hp:run><hp:t>가<hp:tab/>나<hp:lineBreak/>다</hp:t></hp:run></hp:p>')
    assert b[0]["text"] == "가\t나\n다"

def test_change_track_drops_deleted():
    # ChangeTrack.hwpx: "변경<deleteBegin/> 추적<deleteEnd/> <tab/><insertBegin/>인간은<insertEnd/>"
    t = flat_text(all_blocks(FIX / "ChangeTrack.hwpx"))
    assert "변경 \t인간은" in t and "추적" not in t

def test_switch_reads_default_only(tmp_path):
    inner = '<hp:p><hp:run><hp:switch><hp:case><hp:t>A</hp:t></hp:case><hp:default><hp:t>B</hp:t></hp:default></hp:switch></hp:run></hp:p>'
    assert blocks_of(tmp_path, inner)[0][0]["text"] == "B"

def test_page_break_block(tmp_path):
    b, _ = blocks_of(tmp_path, '<hp:p pageBreak="1"><hp:run><hp:t>x</hp:t></hp:run></hp:p>')
    assert [x["type"] for x in b] == ["page_break", "paragraph"]

def test_hidden_comment_not_in_body(tmp_path):
    inner = para_raw('<hp:t>본문</hp:t><hp:ctrl><hp:hiddenComment><hp:subList>'
                     '<hp:p><hp:run><hp:t>숨은 설명</hp:t></hp:run></hp:p></hp:subList></hp:hiddenComment></hp:ctrl>')
    b, ctx = blocks_of(tmp_path, inner)
    assert b[0]["text"] == "본문"
    assert [h["text"] for h in ctx.hidden_comments] == ["숨은 설명"]

def test_hypen_element(tmp_path):
    b, _ = blocks_of(tmp_path, para_raw('<hp:t>재<hp:hypen/>난</hp:t>'))
    assert b[0]["text"] == "재-난"

def test_unknown_object_recorded_as_loss(tmp_path):
    b, ctx = blocks_of(tmp_path, '<hp:p><hp:run><hp:ole/><hp:t>x</hp:t></hp:run></hp:p>')
    assert b[0]["text"] == "x" and "ole" in ctx.losses

def test_char_accounting(tmp_path):
    inner = para_raw('<hp:t>가나<hp:tab/>다</hp:t><hp:ole><hp:t>잃음</hp:t></hp:ole>')
    b, ctx = blocks_of(tmp_path, inner)
    assert (ctx.chars_source, ctx.chars_emitted, lost_chars(ctx)) == (5, 3, 2)

def test_char_accounting_change_track():
    ctx = ctx_of(FIX / "ChangeTrack.hwpx")
    assert ctx.chars_source == ctx.chars_emitted + lost_chars(ctx)

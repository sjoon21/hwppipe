"""손상 입력 회귀 검사: 공개 예제를 고정 시드로 망가뜨려도 처리되지 않은 예외가 없고 글자 수 균형이 맞아야 한다."""
import io
import random
import zipfile

import pytest
from helpers import FIX

from hwppipe import convert

ATTRS = ["rowSpan", "colSpan", "rowAddr", "colAddr", "rowCnt", "colCnt", "level", "num", "idRef", "binaryItemIDRef",
         "beginIDRef", "paraPrIDRef", "charPrIDRef", "borderFillIDRef", "numType", "type", "side"]
TAGS = ["hp:cellAddr", "hp:cellSpan", "hp:subList", "hc:img", "hp:script", "hp:t", "hp:tr", "hp:tc", "hh:paraHead"]


def _mutate(rng: random.Random, data: bytes) -> bytes:
    op = rng.choice(["flip", "cut", "dup", "attr", "tag"])
    s = bytearray(data)
    if op == "flip":
        for _ in range(rng.randint(1, 8)):
            s[rng.randrange(len(s))] = rng.randrange(256)
        return bytes(s)
    if op == "cut":
        return bytes(s[: rng.randrange(len(s))])
    if op == "dup":
        i, j = sorted(rng.sample(range(len(s)), 2))
        return bytes(s[:j] + s[i:j] + s[j:])
    txt = data.decode("utf-8", "ignore")
    if op == "attr":
        for a in ATTRS:
            if rng.random() < 0.3:
                txt = txt.replace(f'{a}="', f'{a}="{rng.choice(["-1", "999999", "x", "", "1e9"])}', 3)
    else:
        for t in TAGS:
            if rng.random() < 0.3:
                txt = txt.replace(f"<{t} ", "<hp:zz ", 2).replace(f"<{t}>", "<hp:zz>", 2)
    return txt.encode()


@pytest.mark.parametrize("seed", range(150))
def test_damaged_input_never_crashes(tmp_path, seed):
    rng = random.Random(seed)
    src = rng.choice(sorted(FIX.glob("*.hwpx")))
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        victim = rng.choice([n for n in names if n.endswith((".xml", ".hpf"))])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as out:
            for n in names:
                if n == victim and rng.random() < 0.1:
                    continue
                out.writestr(n, _mutate(rng, z.read(n)) if n == victim else z.read(n))
    p = tmp_path / "f.hwpx"
    p.write_bytes(buf.getvalue())
    r = convert(p, tmp_path / "o")
    if r["status"] != "skipped":
        c = r["counts"]
        assert c["chars_source"] == c["chars_emitted"] + sum(x["chars"] for x in r["losses"])

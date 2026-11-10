"""실문서 불변식 검사와 제목 추정 평가. HWPPIPE_SAMPLES가 있을 때만 실행한다."""
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
from conftest import SAMPLES
from helpers import assert_heading_chain, read

from hwppipe import convert
from hwppipe.package import open_hwpx
from hwppipe.table import check_grid

GOLD_STEMS = ["2015년_12월_재난안전종합상황_분석_및_전망", "20230728/test", "20251107/test"]


def all_sample_docs():
    return sorted(SAMPLES.rglob("*.hwpx")) if SAMPLES else []


def sample(rel: str) -> Path:
    return next(p for p in SAMPLES.rglob("*.hwpx") if p.as_posix().endswith(rel))


def iter_tables(blocks):
    for b in blocks:
        if b.get("type") == "table":
            yield b
            for c in b["cells"]:
                yield from iter_tables(c["blocks"])
        yield from iter_tables(b.get("blocks", []))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("doc", all_sample_docs(), ids=lambda p: p.relative_to(SAMPLES).as_posix())
def test_invariants(doc, tmp_path):
    r = convert(doc, tmp_path / "a")
    if r["status"] == "skipped":
        pytest.skip(r["skip_reason"])
    out = tmp_path / "a"
    dj = json.loads((out / "document.json").read_text(encoding="utf-8"))
    for t in iter_tables(dj["blocks"]):
        assert check_grid(t) == [], t["id"]
    figs = json.loads((out / "figures.json").read_text(encoding="utf-8"))
    for f in figs:
        if f["file"]:
            assert sha256_file(out / f["file"]) == f["sha256"]
    pkg = open_hwpx(doc)
    embedded = {b.id for b in pkg.bins.values() if b.embedded and pkg.has(b.href)}
    assert {f["binary_id"] for f in figs if f["file"]} >= embedded
    lost = sum(x["chars"] for x in r["losses"])
    assert r["counts"]["chars_source"] == r["counts"]["chars_emitted"] + lost
    assert_heading_chain(dj)
    g = json.loads((out / "graph.json").read_text(encoding="utf-8"))
    ids = [n["id"] for n in g["nodes"]]
    assert len(ids) == len(set(ids)) and all({e["source"], e["target"]} <= set(ids) for e in g["edges"])
    convert(doc, tmp_path / "b")
    for n in ["document.md", "document.json", "graph.json", "figures.json", "report.json"]:
        assert (out / n).read_bytes() == (tmp_path / "b" / n).read_bytes(), n


def test_disaster_doc_counts(tmp_path):
    r = convert(sample("2015년_12월_재난안전종합상황_분석_및_전망.hwpx"), tmp_path)
    assert r["counts"]["tables"] == 110 and r["counts"]["merged_cells"] >= 123
    assert r["counts"]["figures"] == 75


def _norm(text: str) -> str:
    return "".join(text.split())


def score(stem: str, tmp_path: Path) -> tuple[float, float, float]:
    """제목 텍스트(번호 포함, 공백 무시) 다중집합 기준 정밀도·재현율과, 맞힌 제목의 수준 일치율."""
    gold_path = Path(__file__).parent / "fixtures/gold" / (stem.replace("/", "__") + ".headings.json")
    gold = [(_norm(g["text"]), g["level"]) for g in json.loads(gold_path.read_text(encoding="utf-8"))]
    convert(sample(stem + ".hwpx"), tmp_path)
    dj = json.loads((tmp_path / "document.json").read_text(encoding="utf-8"))
    got = [(_norm((b.get("prefix") or "") + b["text"]), b["level"]) for b in dj["blocks"] if b["type"] == "heading"]
    hit = sum((Counter(t for t, _ in gold) & Counter(t for t, _ in got)).values())
    level_hit = sum((Counter(gold) & Counter(got)).values())
    return (hit / len(got) if got else 0.0), (hit / len(gold) if gold else 1.0), (level_hit / hit if hit else 0.0)


@pytest.mark.parametrize("stem", GOLD_STEMS)
def test_heading_precision_recall(stem, tmp_path):
    p, rcl, level_acc = score(stem, tmp_path)
    print(f"{stem}: precision={p:.2f} recall={rcl:.2f} level_agreement={level_acc:.2f}")
    assert p >= 0.8 and rcl >= 0.7, (p, rcl)
    assert level_acc >= 0.7, level_acc

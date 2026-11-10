"""hwppipe 출력으로 RAG 청크를 만드는 예제.

    python examples/chunk_rag.py 문서.hwpx [--max-chars 1200] > chunks.jsonl

- 같은 제목 아래 연속한 블록을 모아 한 청크로 만든다. 블록 중간에서는 자르지 않는다.
- 청크 앞에 제목 경로("1. 개요 > 가. 배경")를 붙인다. 제목 블록 자체는 이 경로로만 나타난다.
- 목록 번호("가.")를 살리고, 본문의 각주 참조([^fn-1])는 각주 내용으로 풀어 넣는다.
- 표는 따로 청크로 만들고 GFM 표로 쓴다(병합은 [병합 행×열]). 길면 행 단위로 나누고 조각마다 머리 행을 반복한다.
- 메타데이터에 원본 블록 id를 남겨 document.json·graph.json과 다시 연결할 수 있게 한다.

한계(예제라서 단순하게 두었다):
- max_chars는 청크의 출력 글자 수 상한이다. 토큰 수가 아니다. 블록 하나나 표의 행 하나가 상한보다 길면 그대로 한 청크가 된다.
- 표의 아래쪽 캡션과 셀 안의 중첩 표는 마지막 조각에 붙인다.
- 그림 청크의 경로(figures/…)는 convert()가 쓴 출력 폴더 기준이다. parse()만 쓰면 그림 파일은 없다.
"""
import argparse
import json
import re
import sys

from hwppipe import parse, to_markdown

NOTE_REF = re.compile(r"\[\^((?:fn|en)-\d+)\]")


def _note_texts(doc: dict) -> dict[str, str]:
    return {n["id"]: " ".join(b.get("text", "") for b in n["blocks"]).strip() for n in doc["notes"]}


def _inline_notes(text: str, notes: dict[str, str]) -> str:
    return NOTE_REF.sub(lambda m: f"(주: {notes[m.group(1)]})" if notes.get(m.group(1)) else "", text)


def _with_path(path: list[str], body: str) -> str:
    head = " > ".join(path)
    return f"{head}\n\n{body}" if head else body


def _block_text(b: dict, notes: dict[str, str]) -> str:
    if b["type"] in ("figure", "textbox"):
        return to_markdown({"blocks": [b]}).strip()
    text = f"{b['prefix']} {b['text']}" if b.get("prefix") and b["type"] == "list_item" else b["text"]
    return _inline_notes(text, notes)


def _table_pieces(md: str, path: list[str], max_chars: int) -> list[str]:
    """GFM 표를 행 단위로 나눈다. 조각마다 표 앞부분(표지·위쪽 캡션)과 머리 행·구분선을 반복한다."""
    lines = md.split("\n")
    start = next((i for i, x in enumerate(lines) if x.startswith("|")), None)
    if start is None or start + 1 >= len(lines):
        return [md]
    end = next((i for i in range(start + 2, len(lines)) if not lines[i].startswith("|")), len(lines))
    head, rows, tail = "\n".join(lines[: start + 2]), lines[start + 2: end], "\n".join(lines[end:]).strip()
    pieces, cur = [], []
    for row in rows:
        if cur and len(_with_path(path, "\n".join([head, *cur, row]))) > max_chars:
            pieces.append("\n".join([head, *cur]))
            cur = []
        cur.append(row)
    pieces.append("\n".join([head, *cur]))
    if tail:
        pieces[-1] += "\n\n" + tail
    return pieces


def chunks(doc: dict, max_chars: int = 1200) -> list[dict]:
    notes = _note_texts(doc)
    out: list[dict] = []
    ids: list[str] = []      # 지금 청크에 들어갈 블록 id(내용이 아직 없는 제목 포함)
    texts: list[str] = []
    path: list[str] | None = None
    section = 0

    def emit(block_ids: list[str], text: str) -> None:
        out.append({
            "id": f"{doc['source']['sha256'][:12]}-{len(out):04d}",
            "text": text,
            "metadata": {"source": doc["source"]["name"], "heading_path": path or [], "block_ids": block_ids,
                         "section": section},
        })

    def flush() -> None:
        nonlocal ids, texts
        if texts:
            emit(ids, _with_path(path or [], "\n".join(texts)))
            ids, texts = [], []

    for b in doc["blocks"]:
        t = b["type"]
        if t == "page_break":
            continue
        if t == "heading" or b["heading_path"] != path:
            flush()
            ids = []  # 내용 없이 끝난 제목은 청크를 만들지 않는다
            path, section = b["heading_path"], b["loc"]["section"]
        if t == "heading":
            ids.append(b["id"])
            continue
        if t == "table":
            flush()  # 앞 글 청크를 먼저 낸다. 내용 없이 남은 제목 id는 표 청크에 붙인다
            md = to_markdown({"blocks": [b]}, table_format="gfm").strip()
            for piece in _table_pieces(md, path or [], max_chars):
                emit(ids + [b["id"]], _with_path(path or [], piece))
            ids = []
            continue
        text = _block_text(b, notes)
        if texts and len(_with_path(path or [], "\n".join(texts + [text]))) > max_chars:
            flush()
        ids.append(b["id"])
        texts.append(text)
    flush()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="HWPX를 RAG 청크(JSONL)로 바꾼다.")
    ap.add_argument("hwpx")
    ap.add_argument("--max-chars", type=int, default=1200,
                    help="청크의 출력 글자 수 상한(토큰 수 아님). 표는 행 단위로 나눈다")
    args = ap.parse_args()
    for c in chunks(parse(args.hwpx), args.max_chars):
        sys.stdout.write(json.dumps(c, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

"""HWPX 문서 하나를 변환해서 출력 폴더에 쓴다."""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from .body import Ctx, parse_section
from .graph import to_graph
from .header import Header, parse_header
from .headings import assign
from .package import HwpxError, Package, Skipped, open_hwpx
from .render_md import render, table_html


def _iter(blocks):
    for b in blocks:
        yield b
        for c in b.get("cells", []):
            yield from _iter(c["blocks"])
        yield from _iter(b.get("blocks", []))


# 1.1: 블록 id, memos[].anchor, tables[].layout, equations[].caption 추가(1과 하위 호환)
# 1.2: equations[].id, headers_footers[].id 추가. 캡션·머리말 블록의 loc.in에 개체 id를 씀
SCHEMA_VERSION = "1.2"
_ID_PREFIX = {"paragraph": "p", "heading": "h", "list_item": "li"}


def _assign_ids(tops: list[dict]) -> None:
    """id가 없는 글 블록(문단·제목·목록 항목)에 문서 순서대로 id를 붙인다. 청킹·그래프에서 블록을 가리키는 데 쓴다."""
    n: dict[str, int] = {}
    for top in tops:
        for b in _iter([top]):
            pre = _ID_PREFIX.get(b.get("type"))
            if pre and "id" not in b:
                n[pre] = n.get(pre, 0) + 1
                b["id"] = f"{pre}-{n[pre]:04d}"


def _strip_private(x):
    if isinstance(x, dict):
        return {k: _strip_private(v) for k, v in x.items() if not k.startswith("_")}
    if isinstance(x, list):
        return [_strip_private(v) for v in x]
    return x


# Windows에서 쓸 수 없는 문자(':'는 대체 데이터 스트림이 된다)와 장치 이름
_WIN_UNSAFE = re.compile(r'[<>:"|?*\x00-\x1f]')
_WIN_RESERVED = re.compile(r"(CON|PRN|AUX|NUL|COM\d|LPT\d)$", re.IGNORECASE)


def _safe_name(bid: str, href: str, used: set[str]) -> str:
    parts = re.split(r"[\\/]", href)
    base = parts[-1]
    ext = base.rsplit(".", 1)[1] if "." in base else ""
    ext = ext if re.fullmatch(r"[A-Za-z0-9]{1,8}", ext) else ""
    bad = (href.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", href) or ".." in parts
           or not base or base in (".", "..") or base.lower() in used
           or _WIN_UNSAFE.search(base) or _WIN_RESERVED.match(base.split(".")[0]))
    name = base
    if bad:
        stem = re.sub(r"[^A-Za-z0-9_-]", "_", bid) or "bin"
        name, n = f"{stem}.{ext}" if ext else stem, 2
        while name.lower() in used:
            name, n = (f"{stem}~{n}.{ext}" if ext else f"{stem}~{n}"), n + 1
    used.add(name.lower())  # 대소문자를 구분하지 않는 파일 시스템에서 서로 덮어쓰지 않게 한다
    return name


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _build(pkg: Package, src: Path) -> tuple[dict, list[dict], dict[str, bytes], dict]:
    try:
        header, header_error = parse_header(pkg.read(pkg.header)), None
    except HwpxError:
        raise
    except Exception as e:  # 글자 모양·번호 정의를 잃어도 본문 글은 살린다(제목 판정과 번호만 약해진다)
        header, header_error = Header(), f"{pkg.header}: {type(e).__name__}: {e}"
    ctx = Ctx(pkg, header)
    sections, partial = [], header_error is not None or not pkg.sections
    if header_error:
        ctx.warnings.append(header_error)
    if not pkg.sections:
        ctx.warnings.append("본문 구역(Contents/section*.xml)을 찾지 못함")
    for i, name in enumerate(pkg.sections):
        m = ctx.mark()
        try:
            sections.append(parse_section(pkg.read(name), i, ctx))
        except HwpxError:
            raise
        except Exception as e:  # 구역 하나가 깨져도 나머지는 살린다. 그 구역에서 쌓인 집계는 되돌린다.
            ctx.rollback(m)
            ctx.warnings.append(f"{name}: {type(e).__name__}: {e}")
            partial = True
    blocks = assign(sections, header)
    _assign_ids([*blocks, *ctx.headers_footers, *ctx.notes])
    doc = {"schema_version": SCHEMA_VERSION, "source": {"name": src.name, "sha256": _sha(src.read_bytes())},
           "metadata": pkg.metadata, "blocks": blocks, "headers_footers": ctx.headers_footers, "notes": ctx.notes,
           "hidden_comments": ctx.hidden_comments, "memos": ctx.memos}

    # 그림 바이너리: manifest 순서로 파일명을 정하고 원본 바이트를 그대로 둔다
    used: set[str] = set()
    files: dict[str, bytes] = {}
    bin_file: dict[str, str] = {}
    for item in pkg.bins.values():
        if item.embedded and pkg.has(item.href):
            name = _safe_name(item.id, item.href, used)
            files[name] = pkg.read(item.href)
            bin_file[item.id] = name

    every = [*blocks, *ctx.headers_footers, *ctx.notes]
    fig_entries, referenced = [], set()
    for top in every:
        for b in _iter([top]):
            if b.get("type") == "figure":
                name = bin_file.get(b["binary_id"] or "")
                b["file"] = f"figures/{name}" if name else None
                item = pkg.bins.get(b["binary_id"] or "")
                if item is not None and item.embedded and not name:
                    ctx.loss("missing_binary_data", b["loc"])
                referenced.add(b["binary_id"])
                in_tbl = b["loc"].get("in", "")
                fig_entries.append(_fig_entry(b, pkg, files.get(name) if name else None,
                                              in_tbl.split("[")[0] if in_tbl.startswith("tbl-") else None,
                                              top.get("heading_path", [])))
    for bid, name in bin_file.items():
        if bid not in referenced:
            item = pkg.bins[bid]
            fig_entries.append({"id": None, "file": f"figures/{name}", "binary_id": bid, "media_type": item.media_type,
                                "sha256": _sha(files[name]), "bytes": len(files[name]), "original_name": None,
                                "pixel_size": None, "caption": None, "in_table": None, "heading_path": None,
                                "loc": None, "referenced": False})
    for top in every:
        for b in _iter([top]):
            if b.get("type") == "table":
                b["html"] = table_html(b)

    report = _report(ctx, blocks, every, partial)
    return _strip_private(doc), fig_entries, files, report


def _fig_entry(b: dict, pkg: Package, data: bytes | None, in_table: str | None, heading_path: list) -> dict:
    item = pkg.bins.get(b["binary_id"] or "")
    return {"id": b["id"], "file": b["file"], "binary_id": b["binary_id"],
            "media_type": item.media_type if item else None,
            "sha256": _sha(data) if data is not None else None, "bytes": len(data) if data is not None else None,
            "original_name": b["original_name"], "pixel_size": b["pixel_size"], "caption": b["caption"],
            "in_table": in_table, "heading_path": heading_path, "loc": b["loc"], "referenced": True}


def _report(ctx: Ctx, blocks: list[dict], every: list[dict], partial: bool) -> dict:
    allb = [b for top in every for b in _iter([top])]
    tables = [b for b in allb if b.get("type") == "table"]
    heads = [b for b in blocks if b["type"] == "heading"]
    losses = [{"kind": k, "count": len(v), "chars": sum(x["chars"] for x in v), "locs": [x["loc"] for x in v]}
              for k, v in sorted(ctx.losses.items())]
    return {
        "status": "partial" if partial else "ok", "skip_reason": None,
        "counts": {
            "tables": len(tables),
            "merged_cells": sum(1 for t in tables for c in t["cells"] if c["rowspan"] > 1 or c["colspan"] > 1),
            "figures": sum(1 for b in allb if b.get("type") == "figure"),
            "equations": sum(len(b.get("equations", [])) for b in allb),
            "footnotes": sum(1 for n in ctx.notes if n["kind"] == "footnote"),
            "endnotes": sum(1 for n in ctx.notes if n["kind"] == "endnote"),
            "memos": len(ctx.memos),
            "headings_outline": sum(1 for b in heads if b["heading_source"] == "outline"),
            "headings_inferred": sum(1 for b in heads if b["heading_source"] == "inferred"),
            "chars_source": ctx.chars_source, "chars_emitted": ctx.chars_emitted,
        },
        "losses": losses, "warnings": ctx.warnings,
    }


_OUTPUT_NAMES = {"document.md", "document.json", "graph.json", "figures", "figures.json", "report.json"}


def _is_previous_output(d: Path) -> bool:
    """hwppipe가 만든 폴더만 교체한다. 다른 파일이 하나라도 있으면 사용자 데이터로 본다."""
    if d.is_dir() and not any(d.iterdir()):
        return True  # 빈 폴더는 잃을 것이 없다
    if not d.is_dir() or not (d / "report.json").is_file():
        return False
    if not {p.name for p in d.iterdir()} <= _OUTPUT_NAMES:
        return False
    figures = d / "figures"
    return not figures.exists() or (figures.is_dir() and all(p.is_file() for p in figures.iterdir()))


def _load(src: Path) -> tuple[dict, list[dict], dict[str, bytes], dict]:
    pkg = open_hwpx(src)
    try:
        return _build(pkg, src)
    finally:
        pkg.close()  # Windows에서 입력 파일이 잠긴 채 남지 않게 한다


def parse(src: Path | str, *, with_report: bool = False) -> dict | tuple[dict, dict]:
    """HWPX를 읽어 document.json과 같은 dict를 돌려준다. 파일은 쓰지 않는다.

    with_report=True면 (doc, report)를 돌려준다. report는 report.json과 같고, status가 partial이면 일부를 잃은 것이다.
    변환할 수 없는 입력(HWP 5.0, 암호 문서, 깨진 패키지)은 Skipped, 크기 한도를 넘는 입력은 HwpxError를 던진다.
    Skipped는 HwpxError의 하위 클래스다.
    """
    src = Path(src)
    doc, _, _, report = _load(src)
    return (doc, report) if with_report else doc


def convert(src: Path | str, out_dir: Path | str, table_format: str = "html", unframe_layout_tables: bool = False) -> dict:
    """src(HWPX)를 변환해 out_dir에 쓴다. 반환값은 report.json 내용이다.

    table_format="gfm"이면 document.md의 표를 HTML 대신 GFM 파이프 표로 쓴다(병합은 [병합 행×열] 주석).
    unframe_layout_tables=True면 document.md에서 테두리가 보이지 않는 틀 표를 문단으로 푼다(document.json은 그대로).
    """
    if table_format not in ("html", "gfm"):
        raise ValueError(f"table_format은 html 또는 gfm이어야 합니다: {table_format}")
    src, out_dir = Path(src), Path(out_dir)
    options = {"table_format": table_format, "unframe_layout_tables": unframe_layout_tables}
    try:
        doc, figs, files, report = _load(src)
        report["options"] = options
    except HwpxError as e:
        reason = e.reason if isinstance(e, Skipped) else f"limit: {e}"
        if (out_dir / "report.json").is_file() and _is_previous_output(out_dir):
            shutil.rmtree(out_dir)  # 이전 변환 결과가 남아 있으면 이번 입력의 결과로 오해한다
        return {"status": "skipped", "skip_reason": reason, "options": options, "counts": {}, "losses": [],
                "warnings": []}

    if out_dir.exists() and not _is_previous_output(out_dir):
        raise FileExistsError(f"hwppipe 출력이 아닌 폴더는 덮어쓰지 않습니다: {out_dir}")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_dir.parent / f".{out_dir.name}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        (tmp / "figures").mkdir(parents=True)
        for name, data in files.items():
            (tmp / "figures" / name).write_bytes(data)
        (tmp / "document.md").write_text(render(doc, table_format, unframe_layout_tables), encoding="utf-8")
        (tmp / "document.json").write_text(_dump(doc), encoding="utf-8")
        (tmp / "graph.json").write_text(_dump(to_graph(doc)), encoding="utf-8")
        (tmp / "figures.json").write_text(_dump(figs), encoding="utf-8")
        (tmp / "report.json").write_text(_dump(report), encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if out_dir.exists():
        shutil.rmtree(out_dir)  # os.replace는 비어 있지 않은 폴더를 덮어쓰지 못한다
    os.replace(tmp, out_dir)
    return report

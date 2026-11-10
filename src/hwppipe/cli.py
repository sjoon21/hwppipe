"""명령줄 진입점: hwppipe <파일|폴더> -o <출력 폴더>"""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .writer import convert


def _convert_one(src: Path, out: Path, *opts) -> dict:
    try:
        r = convert(src, out, *opts)
        entry = {"status": r["status"]}
        if r["status"] == "skipped":
            entry["skip_reason"] = r["skip_reason"]
    except Exception as e:  # 한 문서의 실패가 일괄 처리 전체를 멈추지 않게 한다
        entry = {"status": "error", "error": f"{type(e).__name__}: {e}"}
    print(f"[{entry['status']}] {src}", file=sys.stderr)
    return entry


def _own_summary(p: Path) -> bool:
    """출력 폴더의 report.json이 없거나 hwppipe가 쓴 폴더 요약일 때만 덮어쓴다."""
    try:
        return not p.exists() or "documents" in json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError, TypeError):
        return False


def convert_tree(src: Path, out: Path, *opts) -> dict:
    if not _own_summary(out / "report.json"):
        raise FileExistsError(f"hwppipe가 쓰지 않은 파일은 덮어쓰지 않습니다: {out / 'report.json'}")
    files = sorted((p for p in src.rglob("*") if p.is_file()), key=lambda p: p.relative_to(src).as_posix())
    summary: dict = {"documents": [], "unsupported": [], "collisions": []}
    used: set[str] = set()      # 문서 출력 경로(소문자)
    parents: set[str] = set()   # 문서 출력 경로의 상위 폴더들(소문자)

    def taken(name: str) -> bool:
        # 대소문자 무시 파일 시스템에서 out/a(문서)와 out/A/b(다른 문서의 상위 폴더)는 같은 폴더다
        low = name.lower()
        prefixes = {"/".join(low.split("/")[:i]) for i in range(1, low.count("/") + 1)}
        return low in used or low in parents or bool(prefixes & used) or low == "report.json"  # 요약 파일 자리

    for p in files:
        rel = p.relative_to(src)
        ext = p.suffix.lower()
        if ext == ".hwp":
            summary["unsupported"].append(rel.as_posix())
        if ext != ".hwpx":
            continue
        base = rel.with_suffix("").as_posix()
        name, n = base, 2
        while taken(name):
            name, n = f"{base}~{n}", n + 1
        used.add(name.lower())
        parents.update("/".join(name.lower().split("/")[:i]) for i in range(1, name.count("/") + 1))
        if name != base:
            summary["collisions"].append({"input": rel.as_posix(), "output": name})
        entry = {"input": rel.as_posix(), "output": name, **_convert_one(p, out / name, *opts)}
        summary["documents"].append(entry)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hwppipe", description="HWPX 문서를 RAG·LLM용 결과물로 변환한다.")
    ap.add_argument("--version", action="version", version=f"hwppipe {__version__}")
    ap.add_argument("input", type=Path, help="HWPX 파일 또는 폴더")
    ap.add_argument("-o", "--out", type=Path, required=True, help="출력 폴더")
    ap.add_argument("--table-format", choices=["html", "gfm"], default="html",
                    help="document.md의 표 형식. gfm은 HTML 없이 파이프 표로 쓰고 병합은 [병합 행×열]로 남긴다")
    ap.add_argument("--unframe-layout-tables", action="store_true",
                    help="테두리가 보이지 않는 틀 표를 document.md에서 문단으로 푼다(document.json은 표 구조 유지)")
    args = ap.parse_args(argv)
    if hasattr(sys.stderr, "reconfigure"):  # cp1252 콘솔에서 한글 파일 이름을 출력하다 변환이 멈추지 않게 한다
        sys.stderr.reconfigure(errors="backslashreplace")
    opts = (args.table_format, args.unframe_layout_tables)  # convert(src, out, table_format, unframe_layout_tables) 순서
    if args.input.is_dir():
        src, out = args.input.resolve(), args.out.resolve()
        if out == src or src in out.parents:
            ap.error("출력 폴더는 입력 폴더 안에 둘 수 없습니다(입력 파일을 덮어쓸 수 있음)")
        try:
            summary = convert_tree(args.input, args.out, *opts)
        except FileExistsError as e:
            ap.error(str(e))
        return 1 if any(d["status"] == "error" for d in summary["documents"]) else 0
    if not args.input.is_file():
        ap.error(f"입력을 찾을 수 없습니다: {args.input}")
    entry = _convert_one(args.input, args.out / args.input.stem, *opts)
    return 1 if entry["status"] == "error" else 0


if __name__ == "__main__":
    sys.exit(main())

# hwppipe

HWPX(한글 문서)를 RAG와 지식 그래프에 바로 넣을 수 있는 Markdown·JSON·그래프·그림 원본으로 변환한다. 병합 셀과 중첩 표를 보존하고, 출력에 담지 못한 정보는 손실 보고서에 남긴다.

> **English summary.** hwppipe converts HWPX documents (the XML-based Hangul word-processor format used by Korean government and enterprises) into LLM-ready outputs: Markdown for embedding, block-level JSON for chunking, a node/edge `graph.json` for ontologies and graph databases, and byte-identical figures. Merged and nested table cells are preserved, and anything that could not be represented is listed in a loss report. Pure Python, the only dependency is `lxml`.

> 본 제품은 한컴의 HWP 문서 파일(.hwp) 공개 문서를 참고하여 개발하였습니다.

## 특징

- **표를 잃지 않는다.** `rowspan`·`colspan`과 셀 안의 표를 그대로 살린다. HTML 표 대신 GFM 표(`[병합 2×2]` 주석)로도 쓸 수 있다.
- **구조를 남긴다.** 개요 기능으로 제목을 판정하고, 개요가 없는 공문서는 번호 패턴과 글자 모양으로 제목을 추정한다. 쪽 나눔을 뺀 모든 블록에 `id`와 `loc`(원본 위치)이 붙고, 본문 최상위 블록에는 `heading_path`(속한 제목 계층)가 붙는다.
- **그래프로 내보낸다.** `graph.json`에 구역·제목·문단·표·셀·그림·수식·각주·메모를 노드로, 포함·순서·참조·주석 관계를 엣지로 담는다.
- **본문과 부속을 나눈다.** 머리말·꼬리말, 각주·미주, 글상자, 숨은 설명, 메모를 본문과 섞지 않고 따로 표시한다. 메모에는 작성자와 메모가 붙은 본문 글을 함께 남긴다.
- **수식은 둘 다 남긴다.** LaTeX로 바꾸고 한컴 수식 원문도 함께 둔다.
- **잃은 것을 숨기지 않는다.** 원본 글자 수 = 출력 글자 수 + 손실 글자 수가 항상 맞도록 집계하고, 손실 요소와 위치를 `report.json`에 적는다.
- **입력을 믿지 않는다.** 압축 폭탄 한도, 외부 엔티티를 끈 XML 파서, 경로 조작을 막는 그림 파일 이름을 쓴다. manifest에 암호화가 표시된 문서는 건너뛰고 사유를 남긴다. 일부가 깨진 문서는 살릴 수 있는 만큼 변환한다(손상 입력 퍼징을 테스트에 포함).

## 설치

Python 3.10 이상이 필요하다.

```bash
pip install git+https://github.com/sjoon21/hwppipe
```

개발할 때는 저장소를 받아 `uv sync`로 설치한다.

## 사용

```bash
hwppipe 공문.hwpx -o out/                 # 파일 하나 → out/공문/
hwppipe ./문서함/ -o out/                  # 폴더 → 하위 폴더 구조를 그대로 재현하고 out/report.json에 요약
hwppipe 공문.hwpx -o out/ --table-format gfm          # 표를 HTML 대신 GFM 파이프 표로
hwppipe 공문.hwpx -o out/ --unframe-layout-tables     # 테두리 없는 틀 표를 문단으로 풀어 씀(md에만 적용)
python -m hwppipe --version
```

```python
from hwppipe import parse, to_graph, to_markdown, convert

doc = parse("공문.hwpx")            # 파일을 쓰지 않고 document.json과 같은 dict를 돌려준다
for b in doc["blocks"]:
    if b["type"] != "page_break":
        print(b["id"], b["type"], b["heading_path"], b.get("text", "")[:40])

graph = to_graph(doc)               # {"nodes": [...], "edges": [...]}
markdown = to_markdown(doc, table_format="gfm")

report = convert("공문.hwpx", "out/공문")   # CLI와 같은 파일들을 쓰고 report.json 내용을 돌려준다
```

- `parse()`는 변환할 수 없는 입력(HWP 5.0, 암호 문서, 깨진 패키지)에 `hwppipe.Skipped`를, 크기 한도를 넘는 입력에 `hwppipe.HwpxError`를 던진다. `Skipped`는 `HwpxError`의 하위 클래스다.
- 일부만 변환되었는지 알려면 `doc, report = parse(path, with_report=True)`로 받아 `report["status"]`가 `partial`인지 본다.
- `convert()`는 변환할 수 없는 입력에 예외 대신 `status: "skipped"`를 돌려준다. 다만 hwppipe 출력이 아닌 폴더를 덮어쓰려 하면 `FileExistsError`를, 잘못된 `table_format`에는 `ValueError`를 던진다.

## 출력

```
out/<문서명>/
├── document.md     # 사람과 LLM이 읽는 본문(임베딩 입력)
├── document.json   # 블록 단위 구조 데이터(청킹 입력)
├── graph.json      # 노드·엣지 그래프(온톨로지·그래프 DB 입력)
├── figures/        # HWPX 안의 그림 원본(바이트 단위로 동일)
├── figures.json    # 그림 매니페스트: 원본 이름, 본문 위치, 캡션, 크기, sha256
└── report.json     # 상태·개수·손실·경고
```

`document.md`에서 각 요소는 다음처럼 쓴다.

| 요소 | 표현 |
|------|------|
| 표 | `<!-- table:tbl-001 -->` 다음에 HTML `<table>`. `--table-format gfm`이면 GFM 표와 `[병합 행×열]`, 셀 안 표는 `[표 tbl-002]`로 참조하고 부모 표 뒤에 따로 쓴다. |
| 그림 | `![fig-003: 캡션](figures/image7.png)` |
| 수식 | `$LaTeX$` 다음 줄에 `<!-- hwpeq: 한컴 원본 -->`, 캡션은 그다음 줄 |
| 각주·미주 | `[^fn-1]`, `[^en-1]`. 정의는 문서 끝에 모은다. |
| 머리말·꼬리말 | `> [머리말 · 양쪽] …` |
| 글상자 | `> [글상자] …`. 도형 캡션도 이 안에 쓴다. |
| 숨은 설명 | 문서 끝에 `> [숨은 설명] …` |
| 메모 | 문서 끝에 `> [메모 · 작성자 · 날짜] …`, 다음 줄에 `붙은 글: …` |

예를 들어 병합 셀이 있는 3×3 표는 다음과 같이 나온다.

```markdown
<!-- table:tbl-001 -->
<table><tr><td rowspan="2" colspan="2">1</td><td>2</td></tr><tr><td>3</td></tr><tr><td>5</td><td colspan="2">4</td></tr></table>
```

```markdown
| 1 [병합 2×2] |  | 2 |
| --- | --- | --- |
|  |  | 3 |
| 5 | 4 [병합 1×2] |  |
```

모든 필드와 그래프의 노드·엣지 종류는 [docs/schema.md](docs/schema.md)에 정리했다.

## 지원 범위

| 지원 | 지원하지 않음 |
|------|---------------|
| HWPX(OWPML) 본문·표·그림·묶음 개체·글상자·글맵시·수식·각주·미주·머리말·꼬리말·메모·숨은 설명·변경 추적(삭제 구간 제외)·개요 번호·문단 번호 | `.hwp`(HWP 5.0 바이너리), 암호화된 문서(배포용 문서 판별은 실제 샘플로 검증하지 않음), 차트·OLE 개체 내용, 쪽 번호 같은 조판 결과 |

지원하지 않는 요소를 만나면 `report.json`의 `losses`에 종류와 위치를 기록한다.

## 개발

```bash
uv sync
uv run pytest                                        # 단위 테스트(공개 예제 문서 포함)
bash scripts/fetch-samples.sh                        # 실문서 샘플 17개를 .samples/에 받음
HWPPIPE_SAMPLES=.samples uv run pytest -s            # 실문서 불변식 검사와 제목 추정 평가 포함
```

실문서 샘플은 [hwpxlib](https://github.com/neolord0/hwpxlib)의 `testFile/error`(Apache-2.0)다. 제목 추정 정답은 `tests/fixtures/gold/`에 있다. 실문서 테스트는 표 격자의 정합성, 그림 해시, 글자 수 균형, 그래프 엣지의 끝점과 제목 계층(`heading_path`와 일치), 같은 입력에 같은 출력이 나오는지를 검사한다.

## 라이선스

MIT. 포함한 서드파티 자료는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 적었다.

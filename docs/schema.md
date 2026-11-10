# 출력 형식

hwppipe는 문서 하나를 다음 파일로 바꾼다. 이 문서는 각 파일의 필드를 설명한다.

| 파일 | 용도 |
|------|------|
| `document.md` | 사람과 LLM이 읽는 본문. 임베딩·요약 입력으로 쓴다. |
| `document.json` | 블록 단위 구조 데이터. 청킹·메타데이터 필터링에 쓴다. |
| `graph.json` | 노드·엣지 그래프. 온톨로지 구축과 그래프 DB 적재에 쓴다. |
| `figures/`, `figures.json` | 그림 원본 바이트와 매니페스트 |
| `report.json` | 변환 상태, 개수 집계, 손실·경고 |

Python에서는 `parse()`가 `document.json`과 같은 dict를 돌려주고, `to_markdown()`과 `to_graph()`가 그 dict로 나머지를 만든다.

## document.json

`schema_version`은 `"1.2"`이다. 필드를 추가할 때는 소수점 아래를 올리고, 기존 필드의 뜻을 바꿀 때는 정수 부분을 올린다. 0.x 버전 동안은 소수점 아래 변경에서도 값의 형식(예: `loc.in`)이 바뀔 수 있으니, 변경 기록을 확인한다.

### 최상위

| 필드 | 내용 |
|------|------|
| `source` | `{name, sha256}`: 입력 파일 이름과 해시 |
| `metadata` | `content.hpf`의 제목·작성자·작성일 등. 문서마다 키가 다르다. |
| `blocks` | 본문 블록 목록(읽는 순서) |
| `headers_footers` | 머리말·꼬리말: `{id: header-001\|footer-001, kind: header\|footer, apply: BOTH\|ODD\|EVEN, section, blocks}` |
| `notes` | 각주·미주: `{id: fn-1\|en-1, kind: footnote\|endnote, blocks}` |
| `memos` | 한글 메모: `{id, author, created, number, loc, text, anchor}`. `anchor`는 메모가 붙은 본문 글이다. 범위를 알 수 없으면 `null`이다. |
| `hidden_comments` | 숨은 설명: `{loc, text}` |

### 블록

**id 규칙.** id는 문서 하나 안에서 겹치지 않는 문자열이다. 같은 입력을 같은 버전으로 변환하면 항상 같은 id가 나온다. 문서를 고치거나 hwppipe 버전이 바뀌면 달라질 수 있다. 번호의 자릿수(`p-0001`, `tbl-001`)는 보장하지 않으므로 id를 잘라 해석하지 말고 통째로 비교한다.


모든 블록에는 `type`과 `loc`이 있고, 최상위 블록에는 `heading_path`(상위부터 나열한 속한 제목 목록. 제목 블록은 자기 자신도 포함)가 있다. `page_break`를 뺀 모든 블록에는 문서 안에서 겹치지 않는 `id`가 있다.

| `type` | `id` 형식 | 주요 필드 |
|--------|-----------|-----------|
| `paragraph` | `p-0001` | `text`, `equations` |
| `heading` | `h-0001` | `text`, `level`(1부터), `prefix`(번호), `heading_source`(`outline`: 개요 기능, `inferred`: 번호·글자 모양으로 추정), `equations` |
| `list_item` | `li-0001` | `text`, `level`, `prefix`(번호 또는 `-`), `equations` |
| `table` | `tbl-001` | `rows`, `cols`, `cells`, `caption`, `caption_side`, `layout`, `html` |
| `figure` | `fig-001` | `file`(`figures/…`), `binary_id`, `original_name`, `pixel_size`, `caption`, `caption_side` |
| `textbox` | `box-001` | `blocks`, `caption`, `caption_side` |
| `page_break` | 없음 | 쪽 나눔 |

- `equations`: `{id, script, latex, caption?, caption_side?}` 목록이다. `id`는 `eq-001` 형식이다. `script`는 한컴 수식 원문이고, `latex`는 변환에 실패하면 `null`이다.
- `cells`: `{row, col, rowspan, colspan, header, blocks}` 목록이다. 병합으로 가려진 칸은 목록에 없다. 셀의 `blocks`에는 중첩 표가 들어갈 수 있다.
- `layout`: 모든 셀의 테두리가 보이지 않는 표면 `true`다. 레이아웃용 틀일 가능성이 높다는 표시이며, 구조는 그대로 둔다.
- `loc`: `{section, para, in?}`. `in`은 블록이 들어 있는 곳이다. 예: `tbl-001[0,2]`(표의 0행 2열), `box-003`, `fn-1`, `header-001`, `tbl-001:caption`(표 tbl-001의 캡션), `memo`, `hidden`.

### 원문이 hp:t 밖에 있는 글자

| 요소 | `text`에 들어가는 형태 |
|------|----------------------|
| 글자 겹치기 | 겹친 글자를 순서대로(`composeText`) |
| 덧말 | `본말(덧말)` |
| 체크 상자, 라디오 단추 | `☑ 이름`/`☐ 이름`, `◉ 이름`/`○ 이름`(선택 여부) |
| 명령 단추 | `[이름]` |
| 입력란, 콤보·목록 상자 | 입력값·선택값. 암호 입력란(`passwordChar`가 비어 있지 않거나 없음)은 값을 내보내지 않고 `losses`에 `password_field`로 기록한다 |

표시 기호와 괄호는 hwppipe가 붙인 것이라 `chars_source`·`chars_emitted`에 세지 않는다. 메모의 붙은 글(`anchor`)에는 이 기호도 본문과 똑같이 들어간다.

## graph.json

`document.json`을 노드와 엣지로 바꾼 것이다. 노드 `id`는 `document.json`의 블록 `id`와 같으므로 두 파일을 오가며 쓸 수 있다.

```json
{"schema_version": "1",
 "nodes": [{"id": "h-0001", "type": "Heading", "text": "1. 개요", "level": 1, "loc_section": 0, "loc_para": 3}],
 "edges": [{"source": "sec-0", "target": "h-0001", "type": "CONTAINS"}]}
```

| 노드 `type` | `id` | 속성 |
|-------------|------|------|
| `Document` | `doc` | `name`, `sha256`, `metadata`의 키 |
| `Section` | `sec-0` | `index` |
| `Heading`, `Paragraph`, `ListItem` | 블록 `id` | `text`, `heading_path`, `level`, `prefix` |
| `Table` | `tbl-001` | `rows`, `cols`, `layout`, `caption` |
| `Cell` | `tbl-001[0,2]` | `row`, `col`, `rowspan`, `colspan`, `header` |
| `Figure` | `fig-001` | `file`, `original_name`, `caption` |
| `TextBox` | `box-001` | `caption` |
| `Equation` | `eq-001` | `script`, `latex`, `caption` |
| `Footnote`, `Endnote` | `fn-1`, `en-1` | |
| `Header`, `Footer` | `header-001`, `footer-001` | `apply` |
| `Memo` | `memo-001` | `text`, `author`, `created`, `anchor` |
| `HiddenComment` | `hidden-001` | `text` |

값이 없는 속성은 노드에 넣지 않는다. 원본 위치는 그래프 DB 속성으로 바로 넣을 수 있게 `loc_section`, `loc_para`, `loc_in`으로 펼친다. 모든 속성 값은 문자열·숫자·불리언 또는 문자열 목록이다.

| 엣지 `type` | 방향 | 뜻 |
|-------------|------|----|
| `HAS_SECTION` | Document → Section | 구역 |
| `CONTAINS` | Section·Heading → 블록, Cell·TextBox·각주·머리말 → 블록 | 포함. 제목 아래 블록은 그 제목에 속하고, 하위 제목은 상위 제목에 속한다. |
| `NEXT` | 블록 → 블록 | 읽는 순서. 본문 최상위 블록은 제목 계층과 상관없이 문서 전체 순서로 잇는다(제목 → 그 아래 첫 문단 포함). 셀·글상자·각주·머리말 안에서는 같은 부모 안의 순서다. |
| `HAS_CELL` | Table → Cell | 셀 |
| `HAS_EQUATION` | 블록 → Equation | 문단 안 수식 |
| `REFERS_TO` | 블록 → Footnote·Endnote | 본문의 각주 참조 |
| `HAS_NOTE` | Document → Footnote·Endnote | 각주 정의 |
| `HAS_HEADER`, `HAS_FOOTER` | Section → Header·Footer | 머리말·꼬리말 |
| `ANNOTATES` | Memo·HiddenComment → 블록 | 메모가 달린 문단. 캡션 안 메모는 캡션이 달린 개체, 그 위치에 블록이 없으면 구역 |

Neo4j(APOC)로 적재하는 예다. 노드 id는 문서 하나 안에서만 고유하므로, 여러 문서를 한 DB에 넣을 때는 `Document`의 `sha256`을 붙여 구분한다.

```cypher
CREATE INDEX node_id IF NOT EXISTS FOR (n:Node) ON (n.id);

CALL apoc.load.json("file:///graph.json") YIELD value
UNWIND value.nodes AS n
CALL apoc.create.node(["Node", n.type], n) YIELD node
RETURN count(node);

CALL apoc.load.json("file:///graph.json") YIELD value
UNWIND value.edges AS e
MATCH (a:Node {id: e.source}), (b:Node {id: e.target})
CALL apoc.create.relationship(a, e.type, {}, b) YIELD rel
RETURN count(rel);
```

## figures.json

그림 하나당 항목 하나다. 본문에서 참조하지 않는 그림도 `referenced: false`로 넣는다.

| 필드 | 내용 |
|------|------|
| `id` | 본문 그림 블록의 `id`. 참조되지 않은 그림은 `null` |
| `file`, `binary_id`, `media_type` | 출력 파일 경로, HWPX 안 바이너리 id, MIME 형식 |
| `sha256`, `bytes` | 원본 바이트의 해시와 크기. 바이트는 바꾸지 않는다. |
| `original_name`, `pixel_size` | 한글이 기록한 원본 그림 이름과 픽셀 크기 |
| `caption`, `in_table`, `heading_path`, `loc` | 본문 위치 정보 |

## report.json

| 필드 | 내용 |
|------|------|
| `status` | `ok`, `partial`(깨진 구역을 건너뛰었거나, 깨진 `header.xml` 없이 본문만 변환했거나, 본문 구역을 찾지 못함), `skipped` |
| `skip_reason` | `hwp5`, `not_zip`, `not_hwpx`, `encrypted`, `broken_package`(`content.hpf`·`manifest.xml`이 깨짐), `limit: …`(압축 해제 크기·항목 수 한도 초과) |
| `options` | 변환에 쓴 `table_format`, `unframe_layout_tables` |
| `counts` | 표·병합 셀·그림·수식·각주·미주·메모·제목 개수와 `chars_source`, `chars_emitted` |
| `losses` | 출력에 담지 못한 요소: `{kind, count, chars, locs}` |
| `warnings` | 변경 추적 구간 제외, 짝 없는 메모 등 |

`chars_source`는 원본 글자 수(공백 포함, 공백뿐인 문단 제외), `chars_emitted`는 출력한 글자 수다. 변환된 문서(`ok`, `partial`)에서는 항상 `chars_source == chars_emitted + Σ losses[].chars`가 성립한다. 이 식으로 글자를 조용히 잃지 않았는지 검사할 수 있다.

폴더를 변환하면 출력 폴더 맨 위에 `report.json` 요약이 하나 더 생긴다: `{documents: [{input, output, status}], unsupported: [.hwp 파일], collisions: [...]}`.

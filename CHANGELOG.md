# 변경 기록

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 버전은 [유의적 버전](https://semver.org/lang/ko/)을 따른다.

## [0.2.0] - 2026-11-10

### 추가
- `graph.json`: 구역·제목·문단·표·셀·그림·수식·각주·머리말·메모를 노드로, 포함·순서·셀·참조·주석 관계를 엣지로 내보낸다. 온톨로지 구축과 그래프 DB 적재용이다.
- Python API `parse()`, `to_markdown()`, `to_graph()`. `parse()`는 파일을 쓰지 않는다.
- 모든 블록에 문서 안에서 겹치지 않는 `id`를 붙인다(`p-0001`, `h-0001`, `li-0001`).
- `--table-format gfm`: HTML 없이 GFM 표로 쓰고 병합은 `[병합 행×열]`로 남긴다.
- 틀 표 판정(`tables[].layout`)과 `--unframe-layout-tables`.
- 메모가 붙은 본문 글(`memos[].anchor`), 수식 캡션, 캡션 자동 번호("그림 1", "표(III)").
- 도형·글상자 캡션과 한글 메모 출력.
- `report.json`의 `options`, `--version`, `python -m hwppipe`.
- 실문서 샘플 받기 스크립트(`scripts/fetch-samples.sh`)와 제목 추정 정답.
- `parse(path, with_report=True)`로 일부 변환(`partial`) 여부를 함께 받는다.
- 선언된 크기만 큰 표(25만 칸 초과)는 그 표만 손실로 기록하고, 표 하나의 격자 경고는 5개까지만 남긴다.

### 바뀜
- `document.json`의 `schema_version`을 `1.1`로 올렸다. 필드만 추가했으므로 1과 하위 호환된다.
- 패키지 라이선스 표기를 `MIT AND Apache-2.0`으로 바꾸고(수식 기호표), Apache 원문을 wheel에 함께 넣는다.
- 각주 정의의 둘째 줄부터 4칸 들여 쓴다. 각주 안의 표와 여러 문단이 각주 안에 남는다.

### 고침
- 제목 수준을 건너뛰는 문서(1→3→3)에서 `heading_path`에 형제 제목이 상위 제목처럼 쌓이던 문제
- 폴더 변환이 출력 폴더에 있던 다른 `report.json`을 덮어쓰던 문제
- 변환을 건너뛸 때 같은 폴더의 이전 결과가 남아 이번 결과로 오해되던 문제
- Windows에서 쓸 수 없는 그림 파일 이름(`:`, `CON` 등)
- GFM 표 뒤의 캡션이 표의 한 행으로 읽히던 문제
- 깨진 `header.xml`·`content.hpf`·`manifest.xml`에서 처리되지 않은 예외가 나던 문제. `header.xml`이 깨지면 본문만 변환해 `partial`로, 패키지 파일이 깨지면 `broken_package`로 건너뛴다. 손상 입력 퍼징을 회귀 테스트로 넣었다.
- `fieldEnd`가 없는 메모가 구역 끝까지 본문을 붙은 글로 잡던 문제
- 표 셀·제목·목록 항목 안 수식의 캡션이 Markdown에서 빠지던 문제
- 틀 표를 풀 때 캡션이 사라지던 문제

## [0.1.0] - 2026-11-05

### 추가
- HWPX를 Markdown·JSON·그림 원본·손실 보고서로 변환하는 첫 버전
- 병합 셀·중첩 표 복원, 수식 LaTeX 변환, 각주·미주, 머리말·꼬리말, 변경 추적 처리
- 개요 제목과 번호, 개요가 없는 문서의 제목 추정, `heading_path`
- 폴더 일괄 변환과 요약 보고서

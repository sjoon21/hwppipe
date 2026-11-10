# 기여 안내

버그 제보, 문서 개선, 코드 기여를 모두 환영한다. 아래 순서를 따르면 검토가 빠르다.

## 이슈

- 변환 결과가 이상하면 `report.json`(특히 `losses`, `warnings`)과 hwppipe 버전(`hwppipe --version`)을 함께 적는다.
- 문서를 공개할 수 없으면 같은 문제가 나는 최소 HWPX를 만들어 붙이거나, 문제 요소의 XML 조각만 적는다. 개인정보가 든 문서는 올리지 않는다.

## 개발 환경

```bash
uv sync
uv run pytest                                  # 단위 테스트
bash scripts/fetch-samples.sh                  # 실문서 샘플 17개(.samples/)
HWPPIPE_SAMPLES=.samples uv run pytest -s      # 실문서 불변식·제목 추정 평가
bash scripts/fetch-corpus.sh                   # 대량 검사용 말뭉치 3,169개(.samples/corpus/, 약 5분)
```

## 변경을 보낼 때

- **테스트를 먼저 쓴다.** 고치려는 문제를 재현하는 테스트가 실패하는 것을 확인한 뒤 고친다. 합성 문서는 `tests/helpers.py`의 `make_hwpx`·`para`·`para_raw`·`tbl_xml`로 만든다.
- **글자를 조용히 잃지 않는다.** 새 요소를 처리하면 `chars_source == chars_emitted + Σ losses[].chars`가 계속 성립해야 한다. 처리하지 못하는 요소는 `ctx.loss()`로 기록한다.
- **출력 형식을 바꾸면 문서도 바꾼다.** `docs/schema.md`를 고치고, `document.json`의 필드가 바뀌면 `writer.SCHEMA_VERSION`을 올린다(추가는 소수점 아래, 뜻 변경은 정수 부분).
- **변경 기록을 남긴다.** `CHANGELOG.md`의 맨 위 버전에 사용자가 알아야 할 변화를 적는다.
- 의존성은 `lxml` 하나로 유지한다. 새 의존성이 꼭 필요하면 이슈에서 먼저 논의한다.

## 커밋 메시지

`<type>: <설명>` 형식을 쓴다. type은 `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci` 가운데 하나다.

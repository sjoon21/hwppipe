# Third-Party Notices

## hwpxlib (테스트 파일)

- https://github.com/neolord0/hwpxlib
- Apache License 2.0
- `tests/fixtures/hwpxlib/`의 테스트 파일. 원문 라이선스는 `tests/fixtures/hwpxlib/license.txt`에 있다.
- `tests/fixtures/gold/`의 제목 정답은 hwpxlib `testFile/error`의 문서 3개에서 제목 글을 뽑아 만들었다. 문서 자체는 저장소에 넣지 않고 `scripts/fetch-samples.sh`로 받는다.

## hml-equation-parser (수식 기호 대응표)

- https://github.com/OpenBapul/hml-equation-parser (커밋 c0997f2e19c317d3864a60b7fdf2b5b5cb6899b6)
- Apache License 2.0, Copyright OpenBapul
- `src/hwppipe/_eqsymbols.py`의 기호 대응표를 `convertMap.json`에서 가져왔다. 파서는 hwppipe가 새로 작성했다.
- 라이선스 원문: `LICENSES/Apache-2.0.txt`. 배포 패키지(wheel)에도 함께 들어간다.

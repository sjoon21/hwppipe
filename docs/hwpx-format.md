# HWPX 포맷 조사 노트

- 조사일: 2026-11-05
- 범위: 정부 HWP→HWPX 전환 동향, HWPX(OWPML) 패키지·XML 구조, 한컴 공식 도구, 오픈소스 생태계, 파싱 함정
- 검증 방법: 웹 문서와 함께 **실제 HWPX 샘플을 내려받아 압축을 풀고 XML을 직접 확인했다**. 샘플은 neolord0/hwpxlib 저장소의 테스트 파일이다(Apache-2.0, <https://github.com/neolord0/hwpxlib/tree/main/testFile>).
  - `reader_writer/SimpleTable.hwpx`, `SimplePicture.hwpx`, `SimpleEquation.hwpx`, `HeaderFooter.hwpx`, `ChangeTrack.hwpx`, `PageFunctions.hwpx`, `MultiColumn.hwpx`, `sample1.hwpx`
  - `tool/textextractor/ParaHead.hwpx` (개요·번호·글머리표)
  - `error/20250808/2015년_12월_재난안전종합상황_분석_및_전망.hwpx` (실제 공공 문서: 표 110개, 그림 75개)
  - `error/20250523/프로젝트 계획서.hwpx`, `error/20240626/no_manifest.hwpx`
- 표기: "**[샘플 확인]**"은 위 샘플 XML에서 직접 본 사실이다. "**미확인**"은 근거를 찾지 못했거나 2차 출처뿐인 내용이다.

---

## 1. 정부의 HWP→HWPX 전환

| 시점 | 내용 | 출처 |
|---|---|---|
| 2022년 | 중앙부처 온나라시스템에서 hwpx 사용 의무화 | MTN 2026-04-24 <https://news.mtn.co.kr/news-detail/2026042407250110165> |
| 2026-04-24 | 국가인공지능전략위원회·행정안전부·문화체육관광부가 공공 문서 유통 채널의 hwp 첨부 제한과 hwpx 전환 추진을 발표 | MTN(위 링크), 헤럴드경제 <https://www.heraldk.com/article/2026042316000053545> |
| 2026년 5월 | 온나라시스템 hwp 첨부 제한을 지방정부까지 확대. 공직자통합메일에 hwpx 권고 팝업 | MTN(위 링크) |
| 2026-05 (국무회의 의결) | 「행정업무의 운영 및 혁신에 관한 규정」 개정. 행정기관장이 "인공지능 등에 활용하기 위하여" 개방형 문서 형식으로 문서를 처리하도록 의무화. 조문에는 "hwpx"라는 단어가 직접 나오지 않는다 | 헤럴드경제 <https://www.heraldk.com/article/2026051119551261037>, 조문 <https://www.nepla.ai/law/%ED%96%89%EC%A0%95%EC%97%85%EB%AC%B4%EC%9D%98-%EC%9A%B4%EC%98%81-%EB%B0%8F-%ED%98%81%EC%8B%A0%EC%97%90-%EA%B4%80%ED%95%9C-%EA%B7%9C%EC%A0%95> |
| 2026년 10월 | 온메일(공무원 간)과 공직자통합메일(대국민)에서 hwp 첨부 제한 | MTN(위 링크), JTBC 윤호중 장관 발언 |
| 2026-11-03 국무회의 / 11-04 보도 | 이재명 대통령이 "기계가 읽을 수 없는 문서를 생산하고 있다"며 질타하고, HWPX 전환 지침과 기술적 개선을 지시 | JTBC <https://news.jtbc.co.kr/article/NB12326366> |

### JTBC 기사 요지 (2026-11-04 10:27 게시, 14:00 수정)

- 하정우 국가인공지능전략위원회 부위원장: "AI 대전환에 있어서 핵심이 AI가 읽을 수 있는 데이터인데, 문서를 공유할 때 HWPX 형태로 저장해서 공유하는 게 중요하다."
- 윤호중 행정안전부 장관: "이번 10월부터 공직자 통합 메일에서 … HWPX가 아니면 메일에 올라가질 않습니다. 첨부도 안 되고요." 그런데도 각 부처가 여전히 HWP를 써서 혼선이 생긴다고 했다.
- 하 부위원장은 새 문서의 기본 저장 형식은 이미 HWPX지만, 예전 HWP 파일은 관습적으로 HWP로 계속 저장된다고 설명했다.
- 대통령은 "이런 단순한 기술적 문제들을 아직도 해결을 못 하고 있을까"라며 지침 마련을 주문했다.

### hwppipe에 주는 시사점

- 공공기관 문서가 대량으로 HWPX로 쌓이고, 기존 HWP를 다시 저장하면서 HWPX로 바뀌는 문서도 늘어난다(MTN). 입력 품질이 "한글이 처음부터 HWPX로 만든 문서"부터 "HWP를 변환한 문서"까지 다양해진다는 뜻이다.
- 한컴은 HWP→HWPX 무료 변환기를 제공하며, 한 번에 30개 파일까지 처리한다(한컴 블로그 <https://blog.hancom.com/hwp-hwpx-data-extraction-format-library/>).
- "한컴이 2021년부터 HWPX를 기본 저장 형식으로 바꿨다"는 서술은 검색 요약에서만 봤다. **미확인**.

---

## 2. HWPX 패키지 구조

### 2.1 표준

- HWPX는 OWPML(Open Word-Processor Markup Language) 기반의 ZIP+XML 포맷이다. 국가표준은 **KS X 6101**이다(dbhyeong 블로그 <https://dbhyeong.github.io/blog/hwp-hwpx-format-parsing-python>).
- 한컴 문서 형식 공개 페이지는 OWPML을 "KS X 6101:2011, 개방형 워드프로세서 마크업 언어(OWPML) 문서 구조"로 소개한다. 원문은 직접 배포하지 않고 KSSN·e나라표준인증으로 안내한다(<https://store.hancom.com/etc/hwpDownload.do>).
- LibreOffice 확장 H2Orestart 소스는 KS X 6101:2018을 참조한다(Debian 소스 <https://sources.debian.org/src/h2orestart/0.7.10-1/source/HwpDoc/paragraph/Ctrl_Table.java>). 2018 개정판의 변경 내용과 그 이후 개정 여부는 **미확인**이다.
- 같은 페이지에서 HWP 5.0(rev 1.3), 배포용 문서(rev 1.2), 수식(rev 1.3), 차트(rev 1.2) 스펙 PDF를 받을 수 있다. 스펙을 참고한 제품은 UI·매뉴얼·도움말·소스코드에 다음 문구를 넣어야 한다: **"본 제품은 한컴의 HWP 문서 파일(.hwp) 공개 문서를 참고하여 개발하였습니다."** (<https://store.hancom.com/etc/hwpDownload.do>). hwppipe가 수식·배포용 스펙을 참고하면 이 고지 의무가 생긴다.

### 2.2 ZIP 레이아웃 [샘플 확인]

`SimplePicture.hwpx`의 실제 엔트리(순서 그대로):

```
mimetype                 (19 bytes, 내용: application/hwp+zip)
version.xml
Contents/header.xml
BinData/image1.jpg
Contents/section0.xml
Preview/PrvText.txt
settings.xml
Preview/PrvImage.png
META-INF/container.xml
Contents/content.hpf
META-INF/manifest.xml
```

| 경로 | 역할 | 비고 |
|---|---|---|
| `mimetype` | 포맷 식별자. 내용은 `application/hwp+zip` [샘플 확인] | hwpxlib은 이 엔트리가 없으면 "HWPX 파일 아님"으로 처리한다(<https://github.com/neolord0/hwpxlib/blob/main/src/main/java/kr/dogfoot/hwpxlib/reader/HWPXReader.java>) |
| `version.xml` | `<hv:HCFVersion tagetApplication="WORDPROCESSOR" major="5" minor="0" micro="5" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="…"/>` [샘플 확인] | 속성명이 `target`이 아니라 **`tagetApplication`**(오타 그대로)이다 |
| `META-INF/container.xml` | OCF 컨테이너. `<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>`, `Preview/PrvText.txt`도 rootfile로 등록 [샘플 확인] | 네임스페이스 `urn:oasis:names:tc:opendocument:xmlns:container` |
| `META-INF/manifest.xml` | ODF manifest. 일반 문서에서는 빈 `<odf:manifest/>`. 암호화 문서는 파일별 `odf:encryption-data`를 담는다 [샘플 확인 + hwpxlib `ElementNames.odf_encryption_data`] | 없는 파일도 있다(`no_manifest.hwpx`) |
| `META-INF/container.rdf` | 패키지 구성 RDF. `pkg#HeaderFile`, `pkg#SectionFile` 등으로 파트 유형 표시 [샘플 확인] | 있을 수도, 없을 수도 있다 |
| `Contents/content.hpf` | OPF 패키지: `opf:metadata`, `opf:manifest`, `opf:spine` [샘플 확인] | 본문 진입점 |
| `Contents/header.xml` | 문서 전역 정의: 글꼴, 글자 모양(charPr), 문단 모양(paraPr), 스타일, 번호·글머리표, 테두리/채우기, 변경 추적 목록 등 [샘플 확인] | HWP의 DocInfo에 해당 |
| `Contents/section0.xml` … `sectionN.xml` | 구역별 본문 [샘플 확인] | 순서는 spine을 따른다 |
| `Contents/masterpage0.xml` | 바탕쪽 [샘플 확인: 공공 문서 샘플] | 네임스페이스 `hm` |
| `BinData/` | 이미지·OLE 등 바이너리 원본 [샘플 확인] | jpg, png, bmp 등 원본 확장자 그대로 |
| `Preview/PrvText.txt`, `Preview/PrvImage.png` | 미리보기 텍스트·썸네일 [샘플 확인] | 본문 추출 대용으로 쓰면 안 된다(잘림) |
| `settings.xml` | `ha:HWPApplicationSetting` / `ha:CaretPosition` 등 앱 설정 [샘플 확인] | 내용 추출과 무관 |
| `Scripts/headerScripts`, `Scripts/sourceScripts` | 문서 매크로 스크립트 [샘플 확인: 프로젝트 계획서.hwpx] | 내용 추출과 무관. 실행하면 안 된다 |
| `Chart/…` | 차트 XML. `hp:chart`의 `chartIDRef`가 ZIP 내부 경로를 가리키고, hwpxlib은 그 경로의 바이너리를 그대로 읽는다(<https://github.com/neolord0/hwpxlib/blob/main/src/main/java/kr/dogfoot/hwpxlib/reader/HWPXReader.java>) | 차트 XML 형식(OOXML chart 계열로 보임, `ooxmlchart` 네임스페이스 선언 존재)은 **미확인** |

### 2.3 content.hpf [샘플 확인]

```xml
<opf:package ...>
  <opf:metadata>
    <opf:title/><opf:language>ko</opf:language>
    <opf:meta name="creator" content="text">fff</opf:meta>
    <opf:meta name="subject" content="text"/>
    <opf:meta name="description" content="text"/>
    <opf:meta name="lastsaveby" content="text">fff</opf:meta>
    <opf:meta name="CreatedDate" content="text">2023-02-14T04:40:00Z</opf:meta>
    <opf:meta name="ModifiedDate" content="text">2023-02-14T04:44:13Z</opf:meta>
    <opf:meta name="date" content="text">2023년 2월 14일 화요일 오후 1:40:00</opf:meta>
    <opf:meta name="keyword" content="text"/>
  </opf:metadata>
  <opf:manifest>
    <opf:item id="header"   href="Contents/header.xml"   media-type="application/xml"/>
    <opf:item id="image1"   href="BinData/image1.jpg"    media-type="image/jpg" isEmbeded="1"/>
    <opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>
    <opf:item id="settings" href="settings.xml"          media-type="application/xml"/>
  </opf:manifest>
  <opf:spine>
    <opf:itemref idref="header" linear="yes"/>
    <opf:itemref idref="section0" linear="yes"/>
  </opf:spine>
</opf:package>
```

- 메타데이터(작성자, 생성·수정일, 주제, 키워드)는 `opf:metadata`에 있다. 출력 메타데이터로 그대로 쓸 수 있다.
- 속성명은 `isEmbeded`(오타 그대로)다. media-type도 표준이 아닌 `image/jpg`를 쓴다.
- 구역 순서는 `opf:spine`의 `itemref` 순서를 따라야 한다. 파일명 정렬에 기대면 안 된다(`section10`이 `section2`보다 앞에 정렬되는 문제).

### 2.4 XML 네임스페이스 [샘플 확인: content.hpf·section0.xml 루트 선언]

| 접두어 | URI | 용도 |
|---|---|---|
| `hs` | `http://www.hancom.co.kr/hwpml/2011/section` | 구역 루트 `hs:sec` |
| `hp` | `http://www.hancom.co.kr/hwpml/2011/paragraph` | 문단·런·텍스트·표·그림·컨트롤 등 본문 대부분 |
| `hp10` | `http://www.hancom.co.kr/hwpml/2016/paragraph` | 2016 확장 |
| `hc` | `http://www.hancom.co.kr/hwpml/2011/core` | 공통 타입(`hc:img`, `hc:pt0`, 행렬, 채우기 브러시, 여백 값) |
| `hh` | `http://www.hancom.co.kr/hwpml/2011/head` | header.xml(`hh:head`) |
| `hm` | `http://www.hancom.co.kr/hwpml/2011/master-page` | 바탕쪽 |
| `hhs` | `http://www.hancom.co.kr/hwpml/2011/history` | 문서 이력 |
| `ha` | `http://www.hancom.co.kr/hwpml/2011/app` | settings.xml |
| `hv` | `http://www.hancom.co.kr/hwpml/2011/version` | version.xml |
| `hpf` | `http://www.hancom.co.kr/schema/2011/hpf` | 패키지 |
| `opf` | `http://www.idpf.org/2007/opf/` (끝에 `/` 포함) | content.hpf |
| `ooxmlchart` | `http://www.hancom.co.kr/hwpml/2016/ooxmlchart` | 차트 |
| `hwpunitchar` | `http://www.hancom.co.kr/hwpml/2016/HwpUnitChar` | `hp:switch/hp:case`의 필수 네임스페이스로 쓰임 |

파싱은 접두어가 아니라 **네임스페이스 URI로 매칭해야 한다**. 접두어는 파일마다 바뀔 수 있다. 다만 실제 파일이 접두어를 바꿔 쓰는지는 **미확인**이다.

### 2.5 본문 골격 [샘플 확인]

```
hs:sec
 └ hp:p  (id, paraPrIDRef, styleIDRef, pageBreak, columnBreak, merged)
    ├ hp:run (charPrIDRef)
    │   ├ hp:secPr      ← 구역 첫 문단 첫 런에만. 용지·여백·각주/미주 설정
    │   ├ hp:ctrl       ← 컨트롤 래퍼(colPr, header, footer, footNote, endNote, fieldBegin/End, pageNum, newNum, bookmark …)
    │   ├ hp:tbl / hp:pic / hp:equation / hp:rect / hp:container / hp:ole / hp:chart … ← 개체는 run의 직계 자식
    │   └ hp:t          ← 텍스트. 혼합 콘텐츠(mixed content)
    └ hp:linesegarray / hp:lineseg  ← 조판 결과(줄 위치). 내용 추출에는 불필요
```

- **텍스트**: `hp:p` > `hp:run` > `hp:t`. 개체 뒤에는 빈 `<hp:t/>`가 자주 붙는다.
- **`hp:t`는 혼합 콘텐츠다** [샘플 확인: ChangeTrack.hwpx]. 텍스트 사이에 `hp:tab`, `hp:lineBreak`, `hp:nbSpace`, `hp:fwSpace`, `hp:hypen`(오타 그대로), `hp:markpenBegin/End`, `hp:titleMark`, `hp:insertBegin/End`, `hp:deleteBegin/End`가 끼어든다. 요소 목록은 hwpxlib `ElementNames.java`(<https://github.com/neolord0/hwpxlib/blob/main/src/main/java/kr/dogfoot/hwpxlib/commonstrings/ElementNames.java>) 기준이다. `.text`만 읽으면 tail 텍스트를 잃는다.

  ```xml
  <hp:t>변경<hp:deleteBegin Id="2" TcId="2"/> 추적<hp:deleteEnd Id="2" TcId="2" paraend="0"/> <hp:tab width="3112" leader="0" type="1"/><hp:insertBegin Id="1" TcId="1"/>인간은<hp:insertEnd Id="1" TcId="1" paraend="0"/></hp:t>
  ```

- **쪽·단 나누기**: `hp:p`의 `pageBreak="1"` / `columnBreak="1"` 속성으로 표시된다 [샘플 확인: 공공 문서에 `pageBreak="1"` 문단 38개]. 구역 경계는 `sectionN.xml` 파일 경계와 같다.
- **단 설정**: `hp:ctrl/hp:colPr`(`type="NEWSPAPER"`, `colCount`, `sameSz`, `hp:colSz`) [샘플 확인].
- **단위**: HWPUNIT = 1/7200인치. `hp:pagePr width="59528" height="84188"`은 A4(210×297mm)다 [샘플 확인 + 계산].

### 2.6 구역 설정 `hp:secPr` [샘플 확인]

자식 요소: `hp:grid`, `hp:startNum`(page/pic/tbl/equation 시작 번호), `hp:visibility`, `hp:lineNumberShape`, `hp:pagePr`(`landscape`, `width`, `height`, `hp:margin header/footer/left/right/top/bottom`), `hp:footNotePr`, `hp:endNotePr`(번호 형식 `hp:autoNumFormat type="DIGIT" suffixChar=")"`, 배치 `hp:placement place="EACH_COLUMN"|"END_OF_DOCUMENT"`), `hp:pageBorderFill`. 속성 `outlineShapeIDRef`는 개요 번호 모양(header.xml `hh:numbering` id)을 가리킨다.

### 2.7 표 [샘플 확인: SimpleTable.hwpx]

```xml
<hp:tbl id="…" numberingType="TABLE" pageBreak="CELL" repeatHeader="1"
        rowCnt="3" colCnt="3" cellSpacing="0" borderFillIDRef="3" noAdjust="0">
  <hp:sz …/><hp:pos treatAsChar="0" …/><hp:outMargin …/><hp:inMargin …/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="3">
      <hp:subList … vertAlign="CENTER">
        <hp:p …><hp:run charPrIDRef="0"><hp:t>1</hp:t></hp:run>…</hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/>
      <hp:cellSpan colSpan="2" rowSpan="2"/>
      <hp:cellSz width="12688" height="5772"/>
      <hp:cellMargin left="510" right="510" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc …> … <hp:cellAddr colAddr="2" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/> …</hp:tc>
  </hp:tr>
  <hp:tr>
    <!-- 병합으로 가려진 (0,1),(1,1) 셀은 아예 없다. 이 행에는 tc가 하나뿐이다 -->
    <hp:tc …> … <hp:cellAddr colAddr="2" rowAddr="1"/> …</hp:tc>
  </hp:tr>
  …
</hp:tbl>
```

핵심:
- 격자 크기는 `hp:tbl`의 `rowCnt`/`colCnt`다.
- 셀 위치는 **`hp:cellAddr`의 `colAddr`/`rowAddr`(0부터)**, 병합은 **`hp:cellSpan`의 `colSpan`/`rowSpan`**이다. 둘 다 `hp:tc`의 속성이 아니라 **자식 요소**다.
- **병합으로 가려진 셀은 XML에 나오지 않는다.** `hp:tr` 안의 `hp:tc` 개수는 행마다 다르다. 그러니 `hp:tr` 안의 순서로 열 위치를 추정하면 안 되고, `cellAddr`로 격자에 배치해야 한다.
- 셀 내용은 `hp:subList` 안의 `hp:p` 목록이다. 셀 안에 문단 여러 개, 그림, **중첩 표**가 들어갈 수 있다 [샘플 확인: 공공 문서에서 `hp:tc` 안의 `hp:tbl` 존재].
- `hp:tc header="1"`은 제목 셀, `hp:tbl repeatHeader="1"`은 쪽이 넘어갈 때 제목 행 반복이다. header 속성의 정확한 의미는 스펙 원문으로 **미확인**이다.
- `hp:tc`의 `name` 속성은 셀 필드 이름이다(서식 문서에서 쓰임, **미확인**).
- `hp:cellzoneList/hp:cellzone`(셀 영역별 테두리·배경)도 있다(hwpxlib ElementNames). 내용과는 무관하다.
- `hp:pos treatAsChar="1"`이면 글자처럼 취급되어 문단 흐름 안에 놓이고, `0`이면 떠 있는 개체다. 표·그림·수식 공통이다.

### 2.8 그림과 BinData 연결 [샘플 확인: SimplePicture.hwpx]

```xml
<hp:run charPrIDRef="0">
  <hp:pic id="1137988260" numberingType="PICTURE" textWrap="SQUARE" href="" instid="64246437" …>
    <hp:orgSz width="17664" height="5975"/><hp:curSz width="25942" height="8775"/>
    <hp:imgRect>…</hp:imgRect><hp:imgClip …/><hp:imgDim dimwidth="40800" dimheight="13800"/>
    <hc:img binaryItemIDRef="image1" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>
    <hp:effects>…</hp:effects>
    <hp:sz …/><hp:pos treatAsChar="0" … vertRelTo="PAPER" horzRelTo="PAPER" …/>
    <hp:shapeComment>그림입니다.
원본 그림의 이름: google.jpg
원본 그림의 크기: 가로 544pixel, 세로 184pixel</hp:shapeComment>
  </hp:pic>
  <hp:t/>
</hp:run>
```

연결 경로:

1. `hp:pic` > **`hc:img@binaryItemIDRef="image1"`**
2. → `Contents/content.hpf`의 **`opf:manifest/opf:item[@id="image1"]`** → `href="BinData/image1.jpg"`, `media-type="image/jpg"`, `isEmbeded="1"`
3. → ZIP 엔트리 `BinData/image1.jpg`를 원본 바이트 그대로 추출하면 된다.

부가 정보:
- `hp:shapeComment`에 **원본 파일명과 픽셀 크기**가 들어 있다(한글이 자동 생성하는 문구). 원본명 복원과 alt 텍스트에 쓸 수 있다. 문구 형식은 언어·버전에 따라 다를 수 있다(**미확인**).
- `hp:pic@href`는 연결(링크) 그림의 외부 경로로 보이며, `isEmbeded="0"`이면 ZIP 안에 바이너리가 없을 가능성이 있다. **미확인**: 실제 링크 그림 샘플은 확인하지 못했다.
- 위치 표시는 `hp:pic`이 놓인 run, 즉 문단 안의 위치가 곧 인라인 앵커다. `treatAsChar="0"`인 떠 있는 그림도 XML상으로는 앵커 문단 안에 있다.

**실제 문서에서 그림이 나타나는 다른 위치** [샘플 확인: 2015 재난안전 공공 문서]:
- `hp:pic` 75개 중 대부분이 **`hp:container`(묶음 개체) 안**에 있다(container 71개). 최상위 run만 훑으면 놓친다. 재귀 탐색이 필요하다.
- **글상자**: `hp:rect` 89개, 그중 `hp:drawText`(도형 안 텍스트, 내부에 `hp:subList`) 38개. 본문 텍스트가 도형 안에 들어간 경우다.
- **배경 이미지**: header.xml의 `hh:borderFill` > `hc:fillBrush` > **`hc:imgBrush` > `hc:img binaryItemIDRef`** (3건). 테두리/배경 채우기용 이미지다. 문단 위치가 없으므로 별도 처리가 필요하다.
- 결론: BinData 파일 수와 본문 `hp:pic` 수가 1:1이 아니다. **manifest 기준으로 모든 바이너리를 추출**하고, 본문에서 참조된 것과 참조되지 않은 것을 구분해 기록하는 방식이 안전하다.

### 2.9 캡션 [샘플 확인: 공공 문서]

```xml
<hp:tbl …>
  …
  <hp:caption side="TOP" fullSz="0" width="8504" gap="850" lastWidth="45439">
    <hp:subList …><hp:p …><hp:run …><hp:t>【최근 10년(’05 ~’14년)간 기상특보 발표 현황 (단위 : 회)】</hp:t></hp:run></hp:p></hp:subList>
  </hp:caption>
  …
</hp:tbl>
```

- 캡션은 표·그림 등 개체의 자식 `hp:caption`(`side`=LEFT/RIGHT/TOP/BOTTOM)이고, 내용은 `hp:subList`다. 개체와 캡션의 소속 관계가 명확하므로 그대로 출력할 수 있다.
- "표 1", "그림 2" 같은 자동 번호는 `hp:autoNum` 컨트롤로 들어간다(hwpxlib ElementNames). 번호 값을 직접 계산해야 하는지는 **미확인**이다.

### 2.10 수식 [샘플 확인: SimpleEquation.hwpx]

```xml
<hp:equation id="…" numberingType="EQUATION" version="Equation Version 60" baseLine="61"
             textColor="#000000" baseUnit="1100" lineMode="CHAR" font="HYhwpEQ">
  <hp:sz …/><hp:pos treatAsChar="1" …/>
  <hp:shapeComment>수식입니다.</hp:shapeComment>
  <hp:script>{"123"} over {123 sqrt {3466}} sum _{34} ^{12}</hp:script>
</hp:equation>
```

- `hp:script`에 **한컴 수식 스크립트 원문**(`over`, `sqrt`, `sum _{} ^{}` 등)이 있다. LaTeX가 아니다. 원문을 손실 없이 보존하고, LaTeX 변환은 선택 기능으로 두는 편이 낫다. 문법은 한컴 수식 스펙 rev 1.3(<https://store.hancom.com/etc/hwpDownload.do>)에 있다.

### 2.11 머리말·꼬리말 [샘플 확인: HeaderFooter.hwpx]

```xml
<hp:ctrl>
  <hp:header id="1" applyPageType="BOTH">
    <hp:subList … textWidth="42520" textHeight="4252">
      <hp:p … styleIDRef="10"><hp:run charPrIDRef="2"><hp:t>머리말 테스트</hp:t></hp:run></hp:p>
    </hp:subList>
  </hp:header>
</hp:ctrl>
```

- `hp:ctrl/hp:header`, `hp:ctrl/hp:footer`이고, `applyPageType`은 BOTH/EVEN/ODD다. 본문 문단 안에 컨트롤로 들어가며, 그 위치부터 적용된다.
- 쪽 번호는 `hp:ctrl/hp:pageNum pos="BOTTOM_CENTER" formatType="DIGIT" sideChar="-"`, 번호 재시작은 `hp:newNum num="23" numType="PAGE"`, 감추기는 `hp:pageHiding` [샘플 확인: PageFunctions.hwpx].

### 2.12 각주·미주 (요소명은 hwpxlib 소스로 확인, 샘플 XML은 미확보)

- 요소: `hp:ctrl/hp:footNote`, `hp:ctrl/hp:endNote`. 속성: `number`, `suffixChar`, `instId`. 본문은 `hp:subList`다(hwpxlib `FootNoteEndNoteWriter.java` <https://github.com/neolord0/hwpxlib/blob/main/src/main/java/kr/dogfoot/hwpxlib/writer/section_xml/ctrl/FootNoteEndNoteWriter.java>).
- 각주가 본문 위치에 인라인으로 들어 있으므로 참조 마커 위치를 정확히 남길 수 있다.
- 번호 형식은 `hp:secPr/hp:footNotePr`에 있다.
- **미확인**: 실제 각주 샘플 XML(속성값 형태, 각주 번호 자동 생성 여부). 테스트 픽스처를 확보해야 한다.

### 2.13 필드·하이퍼링크·책갈피·메모 [샘플 확인: sample1.hwpx + hwpxlib]

```xml
<hp:run><hp:ctrl>
  <hp:fieldBegin id="2134831757" type="CLICK_HERE" name="" editable="1" dirty="0" zorder="-1" fieldid="627272811">
    <hp:parameters cnt="2" name="">
      <hp:integerParam name="Prop">9</hp:integerParam>
      <hp:stringParam name="Command">Clickhere:set:44:Direction:wstring:2:수학 HelpState:wstring:0:  </hp:stringParam>
    </hp:parameters>
  </hp:fieldBegin>
</hp:ctrl></hp:run>
<hp:run charPrIDRef="7"><hp:t>수학</hp:t></hp:run>
<hp:run><hp:ctrl><hp:fieldEnd beginIDRef="2134831757" fieldid="627272811"/></hp:ctrl><hp:t/></hp:run>
```

- 필드는 `fieldBegin` … `fieldEnd`가 **런 경계를 넘는 범위**다. 트리 구조가 아니므로 상태 머신으로 추적해야 한다.
- `type` 값(hwpxlib `FieldType.java`): `CLICK_HERE`, `HYPERLINK`, `BOOKMARK`, `FORMULA`, `SUMMARY`, `USER_INFO`, `DATE`, `DOC_DATE`, `PATH`, `CROSSREF`, `MAILMERGE`, `MEMO`, `PROOFREADING_MARKS`, `PRIVATE_INFO`, `METADATA`, `CITATION`, `BIBLIOGRAPHY`.
- 하이퍼링크 URL은 `HYPERLINK` 필드의 `hp:parameters`(`stringParam name="Command"` 등)에 있을 것으로 보이나, 정확한 파라미터 이름은 **미확인**이다.
- 메모는 `MEMO` 필드다. 메모 모양은 header.xml `memoPr`에 있다. 메모 본문 위치는 **미확인**이다.
- 숨은 설명: `hp:ctrl/hp:hiddenComment`(내부 `hp:subList`). 화면에는 안 보이지만 텍스트가 있다.
- 책갈피: `hp:ctrl/hp:bookmark`. 찾아보기 표시: `hp:indexmark`.

### 2.14 기타 개체 (hwpxlib ElementNames 기준)

`hp:ole`(OLE 개체, BinData 참조), `hp:chart`(chartIDRef), `hp:video`, `hp:textart`, `hp:line`/`hp:rect`/`hp:ellipse`/`hp:arc`/`hp:polygon`/`hp:curve`/`hp:connectLine`, 양식 개체 `hp:btn`/`hp:radioBtn`/`hp:checkBtn`/`hp:comboBox`/`hp:listBox`/`hp:edit`/`hp:scrollBar`, `hp:compose`(글자 겹치기), `hp:dutmal`(덧말: `hp:mainText`/`hp:subText`). 이 중 텍스트를 담는 것은 도형 `hp:drawText`, 양식 개체의 텍스트·항목, `hp:textart`, `hp:dutmal`이다.

### 2.15 `hp:switch` / `hp:case` / `hp:default`

header.xml(문단 모양 여백·줄간격)에 `<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">…</hp:case><hp:default>…</hp:default></hp:switch>`가 있다 [샘플 확인]. 같은 내용이 두 번 나오므로, 순진하게 모든 자손을 순회하면 **중복 추출**이 생긴다. 본문 쪽에서 switch가 쓰이는지는 **미확인**이다(hwpxlib은 switch를 범용 객체로 지원한다).

---

## 3. 이미지 참조 흐름 요약

```
section*.xml                     content.hpf (opf:manifest)                 ZIP
hp:pic ─ hc:img@binaryItemIDRef ─▶ opf:item@id → @href, @media-type ─▶ BinData/imageN.ext
header.xml hc:imgBrush/hc:img ──┘  (@isEmbeded="1" 이면 내장)
hp:ole … (BinData 참조, 속성명 미확인)
```

- id는 `image1`, `image2`처럼 생겼지만 규칙은 보장되지 않는다. 반드시 manifest로 조회해야 한다.
- 원본 바이너리를 그대로 복사하면 "원본 보존" 요구를 만족한다. BMP도 원본 형식으로 나온다 [샘플 확인: 공공 문서 BinData에 .bmp 다수].
- hwpxlib도 manifest의 `href`로 ZIP 엔트리를 읽어 붙인다(`item.attachedFile().data(ZipFileReader.readBinary(item.href(), zipFile))`, HWPXReader.java).

---

## 4. 제목·개요 수준과 스타일 표현

### 4.1 header.xml 구조 [샘플 확인: ParaHead.hwpx]

`hh:head` > `hh:beginNum`, `hh:refList` > `hh:fontfaces`, `hh:borderFills`, `hh:charProperties`(`hh:charPr`), `hh:tabProperties`, `hh:numberings`(`hh:numbering` > `hh:paraHead`), `hh:bullets`(`hh:bullet`), `hh:paraProperties`(`hh:paraPr`), `hh:styles`(`hh:style`), `hh:memoProperties`, `hh:trackChanges`, `hh:trackChangeAuthors` / 이어서 `hh:compatibleDocument`, `hh:docOption`, `hh:trackchageConfig`(오타 그대로).

### 4.2 스타일 [샘플 확인]

```xml
<hh:style id="0" type="PARA" name="바탕글" engName="Normal"    paraPrIDRef="3"  charPrIDRef="0" nextStyleIDRef="0" langID="1042"/>
<hh:style id="2" type="PARA" name="개요 1" engName="Outline 1" paraPrIDRef="10" charPrIDRef="0" …/>
…
<hh:style id="8" type="PARA" name="개요 7" engName="Outline 7" paraPrIDRef="4" …/>
<hh:style id="10" type="PARA" name="머리말" engName="Header" …/>
<hh:style id="11" type="PARA" name="각주"   engName="Footnote" …/>
```

- 본문 `hp:p@styleIDRef` → `hh:style@id`, `hp:p@paraPrIDRef` → `hh:paraPr@id`, `hp:run@charPrIDRef` → `hh:charPr@id`.
- 기본 스타일 이름에 "개요 1"~"개요 7"(Outline 1~7)이 있다. 한글 2020 이후 판은 개요 8~10도 있다고 알려져 있으나 **미확인**이다.

### 4.3 개요 수준: `hh:paraPr/hh:heading` [샘플 확인]

```xml
<hh:paraPr id="10" …><hh:heading type="OUTLINE" idRef="0" level="0"/> …   ← 개요 1
<hh:paraPr id="9"  …><hh:heading type="OUTLINE" idRef="0" level="1"/> …   ← 개요 2
<hh:paraPr id="16" …><hh:heading type="BULLET"  idRef="1" level="0"/> …   ← 글머리표
<hh:paraPr id="24" …><hh:heading type="NUMBER"  idRef="3" level="0"/> …   ← 문단 번호
<hh:paraPr id="0"  …><hh:heading type="NONE"    idRef="0" level="0"/> …   ← 일반
```

- **`type`**: `NONE` | `OUTLINE` | `NUMBER` | `BULLET`
- **`level`**: **0부터** 시작한다(개요 1 = level 0).
- **`idRef`**: NUMBER면 `hh:numbering@id`, BULLET이면 `hh:bullet@id`다. OUTLINE이면 0이며, 실제 개요 번호 모양은 `hp:secPr@outlineShapeIDRef`가 가리키는 `hh:numbering`을 쓰는 것으로 보인다(**미확인**: OUTLINE의 idRef 의미).
- **중요** [샘플 확인]: ParaHead.hwpx의 "개요1", "개요1-1" 문단은 **`styleIDRef="0"`(바탕글)이면서 `paraPrIDRef="19"`(heading OUTLINE level 0)**이다. 즉 **스타일 이름만으로 제목을 판정하면 놓친다.** 판정 우선순위는 `paraPr/heading type="OUTLINE"` + `level`, 그다음 스타일 이름("개요 N"/"Outline N") 순서가 적절하다.
- 실무 공공 문서는 개요 기능 대신 "Ⅰ.", "1.", "가." 같은 수동 번호와 글자 크기·굵게로 제목을 표현하는 경우가 많다. 이때는 구조 정보가 XML에 없으므로 휴리스틱이 필요하다. 이 판단은 일반론이며, 샘플 통계로 검증하지는 않았다(**미확인**).

### 4.4 번호·글머리표 정의 [샘플 확인]

```xml
<hh:numbering id="1" start="0">
  <hh:paraHead start="1" level="1" numFormat="DIGIT"           …>^1.</hh:paraHead>
  <hh:paraHead start="1" level="2" numFormat="HANGUL_SYLLABLE" …>^2.</hh:paraHead>
  <hh:paraHead start="1" level="3" numFormat="DIGIT"           …>^3)</hh:paraHead>
  …
</hh:numbering>
<hh:bullet id="1" char="" useImage="0"><hh:paraHead level="0" …/></hh:bullet>
```

- 번호 서식 문자열은 `^1.`, `^2.`, `(^5)`처럼 `^레벨` 자리표시자를 쓴다. `numFormat`은 DIGIT, HANGUL_SYLLABLE 등이다.
- **자동 번호 텍스트("1.", "가.")는 본문 `hp:t`에 없다.** 원문처럼 보이게 하려면 카운터를 직접 계산해 렌더링해야 한다. `hh:paraHead@level`은 1부터, `hh:heading@level`은 0부터 시작하므로 매핑할 때 1을 더해야 한다.
- 글머리표 `char`는 사설 영역(PUA) 문자일 수 있다[샘플에서 `char=""`로 보임]. 출력할 때 일반 기호로 바꿔야 할 수 있다(**미확인**).

---

## 5. 한컴 공식 도구: Data Loader와 관련 오픈소스

### 5.1 한컴 데이터 로더 (Hancom Data Loader)

| 항목 | 내용 | 출처 |
|---|---|---|
| 성격 | 상용 문서 파싱 솔루션. HWP/HWPX를 PDF로 변환하지 않고 직접 파싱 | <https://blog.hancom.com/hancom-data-loader-startguide/> |
| 입력 | HWP, HWPX, PDF, OOXML(DOCX/XLSX/PPTX), PNG/JPG/BMP | 같은 글, opendataloader-pdf README |
| 기능 | DLA(레이아웃·읽기 순서), TSR(표 구조 복원: 테두리 없는 표, 병합 셀, 중첩 표), OCR. 이미지 캡셔닝은 **PoC 단계, 출시 미정** | <https://blog.hancom.com/hwp-hwpx-data-extraction-format-library/> |
| 출력 | SaaS API: JSON / Solution(온프레미스): JSON, Clientinfo / Studio: JSON, HTML, 뷰어 / TSR: Markdown, JSON, HTML | <https://blog.hancom.com/hancom-data-loader-startguide/> |
| 제공 형태 | SaaS API(페이지당 종량 과금), 온프레미스(컨테이너 설치, 일회성 구매), Data Loader Studio | 같은 글 |
| 가격·한도 | 공개 안 됨. 문의 필요(<https://sdk.hancom.com/contacts/create>) | 같은 글 |
| 라이선스 | 상용. **오픈소스 아님** | 두 블로그 글 모두 상용으로 기술 |
| 데모 | <https://livedemo.sdk.hancom.com/dataloader> | 같은 글 |

**결론**: hwppipe의 의존성으로 쓸 수 없다(비공개·유료·네트워크/컨테이너 의존). 다만 "병합 셀·중첩 표·각주·메타데이터 보존, 읽기 순서, 표는 Markdown/JSON/HTML 출력"이라는 기능 목록은 hwppipe 출력 설계의 비교 기준(벤치마크)으로 쓸 만하다.

### 5.2 OpenDataLoader PDF (한컴 오픈소스)

- <https://github.com/opendataloader-project/opendataloader-pdf>: Apache-2.0, **PDF 전용**이다. README에서 HWP/HWPX 지원은 "Hancom Data Loader Integration — Coming Soon"(상용 연동)으로만 언급한다. HWPX 파서로는 쓸 수 없다.
- 다만 출력 포맷 설계(`format="markdown,json"`, 폴더 입력 지원)는 참고할 만하다.

### 5.3 hancom-io GitHub (한컴 공개 저장소)

| 저장소 | 라이선스 | 내용 |
|---|---|---|
| [hancom-io/hwpx-owpml-model](https://github.com/hancom-io/hwpx-owpml-model) | Apache-2.0 | OWPML 필터 모델(C++, Windows/VS2017 빌드). 텍스트 추출 예제는 "첫번째 섹션에 대한 추출만 가능". 마지막 push 2023-10 |
| [hancom-io/dvc](https://github.com/hancom-io/dvc) | NOASSERTION | HWPX 문서 서식 적합성 검증(C++). owpml-model 사용 |
| [hancom-io/metatag-ex](https://github.com/hancom-io/metatag-ex) | Apache-2.0 | OWPML 모델로 메타태그 추출 |

C++/Windows 빌드 전용이라 파이썬 도구의 의존성으로는 부적합하다. 다만 **한컴이 직접 공개한 OWPML 객체 모델 소스**이므로 요소·속성의 정답 참고 자료로 쓸 가치가 있다.

---

## 6. 서드파티 라이브러리 (2026-11-05 PyPI/GitHub API 조회 기준)

| 이름 | 언어 | 라이선스 | 최신 | 비고 |
|---|---|---|---|---|
| [hwpxlib](https://github.com/neolord0/hwpxlib) | Java | Apache-2.0 | push 2026-08 | 가장 완결된 HWPX 객체 모델. 요소명 상수(`ElementNames.java`)가 사실상 스키마 레퍼런스. 암호화 HWPX는 확장 모듈로만 지원(한컴 블로그) |
| [python-hwpx](https://pypi.org/project/python-hwpx/) | Python | Apache-2.0 (PyPI 6.11.0, 2026-11-02) | 매우 활발 | lxml만 의존. 읽기·편집·생성. 텍스트/HTML/Markdown 내보내기, 중첩 표·각주 보존. **포크(pyr10241024)는 비상업 라이선스로 표기된 적이 있어 버전별 라이선스 확인 필요**(<https://github.com/pyr10241024/python-hwpx>) |
| [hwp-hwpx-parser](https://pypi.org/project/hwp-hwpx-parser/) | Python | Apache-2.0 | 1.0.0 (2026-01-29) | HWP+HWPX 읽기 전용. 텍스트·표·각주·메모 추출. GitHub 저장소 URL이 404(조회 시점) |
| [pyhwpxlib](https://pypi.org/project/pyhwpxlib/) | Python | **PolyForm-Noncommercial-1.0.0 AND Apache-2.0** | 0.18.3 | 비상업 조항이 있어 오픈소스 의존성으로 부적합 |
| [hwpxkit](https://pypi.org/project/hwpxkit/) | Rust+Py | MIT | 0.2.1 | 초기 단계(스타 2) |
| [pyhwpx](https://pypi.org/project/pyhwpx/) | Python | 미표기 | 1.7.2 | "아래아한글 자동화" 모듈. 한글 프로그램 COM 자동화로 알려져 있다(Windows+한글 설치 필요, **미확인**). 서버 파이프라인에 부적합 |
| [pyhwp](https://pypi.org/project/pyhwp/) | Python | AGPL-3.0+ | 0.1b15 (2020-05) | HWP 5.0 전용, HWPX 미지원, 유지보수 중단 |
| [rhwp](https://github.com/edwardkim/rhwp) | Rust/WASM | MIT | 활발(스타 4천+) | HWP 5.0 + HWPX 뷰어/에디터 |
| [H2Orestart](https://github.com/ebandal/H2Orestart) | Java | **GPL-3.0** | 활발 | LibreOffice 확장. KS X 6101:2018 참조 |
| hwp2md (crates.io) | Rust | 미확인 | 0.5.0 | HWPX 읽기/쓰기, Markdown 변환(<https://docs.rs/crate/hwp2md/0.5.0>) |

**의존성 판단 (hwppipe 관점)**:
- HWPX는 ZIP+XML이라 파이썬 표준 라이브러리(`zipfile`)와 XML 파서만으로 파싱할 수 있다. dbhyeong 블로그 저자도 별도 라이브러리 없이 `hp:t`를 직접 읽었다(<https://dbhyeong.github.io/blog/hwp-hwpx-format-parsing-python>).
- 라이브러리를 쓴다면 python-hwpx(Apache-2.0, lxml 의존)가 유일한 현실적 후보다. 다만 편집 지향 API라서 "병합 셀 격자·인라인 그림 앵커·필드 범위" 같은 무손실 추출 요구에 맞는지는 별도 검증이 필요하다(**미확인**).
- GPL(H2Orestart), AGPL(pyhwp), 비상업(pyhwpxlib) 코드는 복사하거나 의존하지 않는다.

---

## 7. 알려진 함정

### 7.1 암호화·배포용 문서

- HWPX 암호화는 **파일 단위**다(HWP는 스트림 전체). 암호화 정보는 `META-INF/manifest.xml`의 `odf:encryption-data`(checksumType, checksum, algorithm, key-derivation, start-key-generation)에 있다. 근거: hwpxlib `EncryptionData.java`(<https://github.com/neolord0/hwpxlib/blob/main/src/main/java/kr/dogfoot/hwpxlib/object/metainf/EncryptionData.java>), 한컴 블로그(<https://blog.hancom.com/hwp-hwpx-data-extraction-format-library/>).
- **배포용 HWPX**: hwpx-decrypt(0BSD, <https://github.com/OctopusET/hwpx-decrypt>, 조회 시점에 저장소 이동됨) README에 따르면 다음과 같다. 출처가 서드파티 1곳뿐이므로 신뢰도는 낮다.
  - 고정 비밀번호를 SHA-256 → PBKDF2-HMAC-SHA1(1024회, salt) → AES-256-CBC → DEFLATE 해제 순서로 처리한다. salt와 IV는 manifest.xml에서 읽는다.
  - 사용자가 지정하는 배포 암호는 쓰기 방지용일 뿐, 암호화 키와 무관하다고 주장한다.
- **정책 제안**: 기술적으로 복호화가 가능해도, 배포용 문서는 작성자가 복사·인쇄를 막으려고 지정한 것이다. 기본 동작은 "감지 후 건너뛰고 사유 기록"으로 두고, 복호화는 하지 않는 편이 안전하다. 법적 판단은 **미확인**이며 별도 검토가 필요하다.
- **사용자 암호(열기 암호) 문서**: 암호 없이는 읽을 수 없다. 감지 후 건너뛴다. 감지 방법은 manifest에 encryption-data가 있는지, 또는 section XML이 파싱되지 않는지로 판단한다(**미확인**: 배포용과 열기 암호를 구분하는 표지).
- **기관 DRM**(Fasoo, SoftCamp 등): 파일 자체가 DRM 컨테이너로 감싸져 있어 ZIP 시그니처(`PK`)가 아니다. 감지 후 건너뛴다(일반론, **미확인**).

### 7.2 변경 추적 [샘플 확인: ChangeTrack.hwpx]

- 삽입·삭제 구간이 `hp:t` 안의 마커(`hp:insertBegin/End`, `hp:deleteBegin/End`, 속성 `Id`, `TcId`, `paraend`)로 표시된다. **삭제된 텍스트도 XML에 그대로 남아 있다.**
- 메타데이터는 header.xml `hh:trackChanges/hh:trackChange`(`type="Insert"|"Delete"`, `date`, `authorID`, `hide`, `id`)와 `hh:trackChangeAuthors`에 있다.
- 마커를 무시하면 **삭제된 문장이 최종본에 섞인다.** 기본값은 "변경 반영본"(삭제 구간 제외)으로 출력하고, 옵션으로 원본/변경 내역을 보존하는 방식을 권한다.
- 문서 이력(`hhs:history`, 버전별 diff)도 별도 파트로 존재할 수 있다(hwpxlib ElementNames). 실제 파일 위치는 **미확인**이다.

### 7.3 숨김 텍스트

- `hp:hiddenComment`(숨은 설명)는 화면에 안 보이지만 텍스트가 있다.
- 글자 모양 수준의 "숨김" 속성(charPr)이 있는지, 그리고 그 속성명은 **미확인**이다.
- 감추기 컨트롤 `hp:pageHiding`은 머리말·쪽 번호를 해당 쪽에서 숨기는 표시일 뿐, 텍스트 숨김이 아니다 [샘플 확인].
- 정책: 숨은 텍스트는 별도 표시를 붙여 보존하고, 본문과 섞지 않는다.

### 7.4 필드

- 누름틀(`CLICK_HERE`)의 안내문(`Direction`)은 `hp:stringParam Command` 안에 있다. 실제 입력값은 `fieldBegin`과 `fieldEnd` 사이 런에 있다 [샘플 확인]. 빈 서식 문서에서는 안내문만 있고 값이 비어 있을 수 있다.
- 날짜·경로·요약 같은 계산 필드의 텍스트가 저장 시점 값으로 들어 있는지는 **미확인**이다.

### 7.5 구조상 함정 [대부분 샘플 확인]

1. **병합 셀은 생략된다**. `cellAddr` 기반 격자 배치가 필수다(2.7절).
2. **`hp:t` 혼합 콘텐츠**. tail 텍스트와 탭·줄바꿈 요소를 함께 처리해야 한다(2.5절).
3. **그림이 묶음 개체(`hp:container`) 안에 중첩**되고, **텍스트가 글상자(`hp:rect/hp:drawText`) 안에** 있다(2.8절). 재귀 탐색이 필요하다.
4. **배경 이미지는 header.xml `hc:imgBrush`**에 있어 본문 위치가 없다.
5. **자동 번호(개요·문단 번호·글머리표)는 본문 텍스트에 없다**. 계산해서 넣어야 한다(4.4절).
6. **제목이 스타일명이 아닌 paraPr heading으로만** 표현될 수 있다(4.3절).
7. **`hp:switch/case/default` 중복**(2.15절).
8. **`hp:linesegarray`는 조판 캐시**라 무시하면 된다. 다만 HWP→HWPX 변환 문서에서 lineseg가 없거나 비정상일 수 있다는 보고가 있다(**미확인**, hwpxlib error 폴더의 존재가 암시).
9. **파일 레벨 변형**: `META-INF/manifest.xml` 누락(`no_manifest.hwpx`), `container.rdf`가 있거나 없음, `Scripts/` 존재, 오타 속성명(`tagetApplication`, `isEmbeded`, `hypen`, `trackchageConfig`)이 있다. 오타를 "고치면" 매칭이 깨진다.
10. **section 순서**는 spine을 따른다(2.3절).
11. **비표준 media-type**(`image/jpg`). 확장자는 href 기준으로 유지한다.
12. **미리보기 텍스트(`PrvText.txt`)는 잘린 요약**이다. 본문 대용으로 쓰지 않는다.
13. **HWP 5.0 바이너리(.hwp)는 별개 포맷**(CFB/OLE + zlib 레코드)이다. 확장자가 .hwpx인데 실제로는 CFB 시그니처(`D0 CF 11 E0`)인 파일, 또는 그 반대가 섞여 들어올 수 있다. 매직 바이트로 판별해야 한다(dbhyeong 블로그의 HWP 구조 설명 참고. 오명명 사례 자체는 **미확인**).

---

## 8. hwppipe 설계에 바로 반영할 결정 후보

- 파서는 표준 라이브러리 `zipfile`과 XML 파서로 직접 구현할 수 있다. 공식·서드파티 모두 "무손실 RAG 추출"을 오픈소스로 제공하는 도구는 확인되지 않았다.
- 요소명 레퍼런스로는 hwpxlib `ElementNames.java`/`AttributeNames.java`(Apache-2.0)와 hancom-io/hwpx-owpml-model을 쓴다.
- 테스트 픽스처로는 hwpxlib `testFile/`(Apache-2.0)과 공공누리 제1유형 공공 문서를 쓴다. 각주·미주·하이퍼링크·메모·OLE·차트·링크 그림 샘플은 아직 확보하지 못했으며, 다음 조사 항목이다.
- 수식 문법이나 배포용 문서 스펙을 참고하면 한컴 고지 문구 의무가 생긴다(2.1절).

## 9. 미확인 항목 정리

- KS X 6101 최신 개정판과 스펙 원문(유료 표준)
- `hh:heading type="OUTLINE"`의 `idRef` 의미, 개요 8~10 지원 여부
- 각주·미주 실제 XML 샘플, 하이퍼링크 URL 파라미터 이름, 메모 본문 위치
- 링크 그림(`isEmbeded="0"`, `hp:pic@href`) 처리, `hp:ole`의 BinData 참조 속성명, 차트 XML 형식
- 숨김 글자 속성, 열기 암호 문서와 배포용 문서의 구분 표지
- 본문에서 `hp:switch`가 쓰이는지, 네임스페이스 접두어가 바뀌는 실제 사례
- "한컴 2021년부터 HWPX 기본 저장" 서술의 1차 출처

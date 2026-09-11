# v10 official-concordance diagnostic

작성: 2026-09-11, dev / mac

## 목적

EXP171 dev200에서 v10·v11·v16·v18·v20의 TP가 모두 0인 원인이 입력 누락인지, card/policy
오류인지, dev label과 제공 source의 불일치인지 분리한다. 이 문서는 v10의 7개 gold-positive를
먼저 확인한 진단이며 규칙 추가나 card 변경 계획이 아니다.

## 관찰

v10 gold-positive는 PPS-DEV-13, 061, 062, 064, 068, 069, 075의 7건이다. 모두 pipeline에
제공된 공고문이 있고 label join 오류는 없다.

- PPS-DEV-13은 공고문에 `직접생산확인증명확인서 각 1부`를 명시하지만 gold v10은 1이다.
  현재 정의가 “적용 대상인데 직접생산확인 요구가 없음”이라면 보이는 source와 정면으로
  충돌한다.
- PPS-DEV-075도 공고문에 `10조에 의한 직접생산증명서`가 있으나 gold v10은 1이다.
- PPS-DEV-064와 069에는 직접생산 기준 위반 시 제재 문구가 있으나, 이것이 입찰자에게
  직접생산확인증명서를 요구하는 조항과 동일한지는 별도 판단이 필요하다.
- PPS-DEV-061, 062, 068의 제공 원문에는 `직접생산` 문자열이 없다.
- 7건의 `세부품명번호목록`은 모두 null이다. 다만 PPS-DEV-13은 공고문에 적힌 exact code가
  organizer 경쟁제품 CSV의 3개 품목과 일치한다(그중 2개는 `특이사항`이 비어 있음).
  나머지 6건의 exact-code lookup은 unknown이다.
- 이 7건에는 `조항호내용=중소벤처기업부장관이 지정 공고한 물품`이라는 공통 upstream
  metadata가 나타나지만, 이것만으로 실제 구매 대상 제품의 exact-code 적용을 Python이
  확정하면 금지된 label rule이 된다.

## 결론

v10의 0 recall을 단순한 source omission으로 설명할 수 없다. 적어도 PPS-DEV-13과 075는
모델에게 보이는 문구와 gold label 사이에 의미 충돌이 있다. 반대로 나머지 사례는 제품
적용 여부가 exact-code input만으로 확정되지 않아, 보수적으로 0을 내는 현재 정책에도
정보 한계가 있다.

따라서 dev v10을 맞추기 위해 `조항호내용`이나 ID를 Python override로 사용하는 것은
공식 의미 정합성을 해친다. 다음 실험은 먼저 v10 truth condition과 주최측 정답 스키마의
해석을 공식 자료에 대조하고, source에 있는 “요구”, “제재 안내”, “단순 언급”을 구분하는
item-local source-only relation을 작은 panel에서 검증해야 한다.

# EXP247 — v10 product applicability and whole-notice presence review

작성: 2026-09-14, dev / mac

## 가설

EXP245는 organizer product catalog를 모두 제공했지만 v10 fast positives를 회복하지 못했다.
단순 정보 추가만으로는 Gemma가 `실제 구매대상 → 고시 제품/적용조건 → 직접생산 요구의
공고 전체 존재` 관계를 실행하지 않는다.

v10-only 같은 응답에서 다음 관찰을 판정보다 먼저 명시하면 적용성과 부재를 분리해 최종
v10을 개선할 수 있다는 최소 가설을 검증한다.

1. 공고가 실제 구매하는 물품·용역.
2. 가장 가까운 organizer catalog 세부품명.
3. 그 행의 적용조건 충족 여부.
4. 경쟁제품 적용/비적용/불명.
5. 직접생산 확인 요구 있음/없음/불명.
6. 존재한다고 판단한 경우의 unchanged source substring.
7. model-owned final v10.

Python은 schema parse와 substring provenance만 기록한다. review 조합으로 v10을 계산하거나
override하지 않는다. v10은 e10이 항상 blank이므로 final은 V-only다.

## 통제와 gate

- base: `configs/config.exp245-v10-full-product-catalog-fast-panel-c4.yaml`.
- sole allowed change: `prompt.mode`.
- full organizer catalog, exact-code fact, v10 card, metadata, all source, V-only output, tokenizer
  admission, provider parameters, merge와 postprocess는 동일하다.
- mode는 v10 하나에만 허용한다. 성공 전 다른 absence item으로 일반화하지 않는다.
- preflight, exact admission/topology, short/attachment/overflow rendered review, active-v10
  semantic contract, parser/malformed tests, exact mock과 49-column validation을 먼저 통과한다.

fast20에서 EXP245 `0/1/2`보다 v10 F1이 개선되고 parse/source failure가 없어야 holdout으로
간다. 후보명을 잘 골라도 최종 label이 개선되지 않으면 schema를 더 늘리지 않고 중단한다.

## Fast20 결과

- preflight는 `prompt.mode` 하나만 달라졌음을 확인했다.
- exact dev200 admission은 374/374 documents와 fixed inputs를 보존했고 omission/over-budget
  0이었다. topology는 165×1 + 18×2 + 17×3 = 252 calls다.
- short/attachment/overflow rendered review에서 catalog와 실제 source 뒤에 구조화 검토가
  배치됨을 확인했다. mock과 219 tests가 통과했다.
- provider run은 20 records / 24 calls, 38.1초, prompt/completion 569,578/4,215 tokens,
  parse error 0이었다.
- v10 TP/FP/FN은 EXP245 `0/1/2`에서 `2/5/0`, F1 `0 -> .444444`로 개선됐다.
  EXP205에 field replacement한 macro는 `.325000 -> .343519`다.
- `PPS-DEV-062`, `PPS-DEV-069` 모두 실제 행사대행 대상, 행사대행서비스 catalog 후보,
  적용조건 충족, 경쟁제품 적용, 직접생산 요구 없음으로 관찰되어 양성을 회복했다.
- 다섯 FP 중 `PPS-DEV-036`, `PPS-DEV-051`은 후보 세부품명을 null로 두고도 경쟁제품 적용을
  적용으로 쓴 내부 모순이다. Python은 이를 label rule로 교정하지 않는다.

target F1과 merged macro가 개선됐고 malformed/source failure가 없으므로 fast gate는 통과했다.
EXP248에서 prompt/schema를 바꾸지 않고 frozen independent holdout20으로 확장한다.

## EXP248 independent holdout20 결과

- preflight는 EXP247과 effective policy difference가 0임을 확인했다.
- exact admission/topology는 EXP247과 동일하고, holdout short/attachment/overflow의 rendered
  contract와 mock validation이 통과했다.
- provider run은 20 records / 23 calls, 29.2초, parse error 0이었다.
- v10 TP/FP/FN은 frozen EXP206 `0/0/1`에서 `1/5/0`, F1 `0 -> .285714`로 개선됐다.
  EXP206에 field replacement한 macro는 `.208333 -> .220238`이다.
- holdout true positive `PPS-DEV-068`은 학습분석시스템 유지보수와
  정보시스템유지관리서비스를 대응하고 직접생산 요구 없음으로 판정했다.

precision은 낮지만 fast와 holdout 모두 기존 zero-recall을 full recall로 바꿨고 방향이
일치한다. 정책을 변경하지 않은 EXP249 dev200 extension으로 승격한다.

## EXP249 dev200 결과

- preflight와 exact mock은 EXP247 대비 effective policy difference 0, 200/200 rows,
  49-column/ID/evidence validation을 통과했다.
- exact admission은 374/374 source documents와 fixed inputs를 보존했고 topology는
  `165×1 + 18×2 + 17×3 = 252 calls`였다.
- provider run은 200 records / 252 calls, 412.1초, prompt/completion
  `5,280,873/71,234` tokens였다.
- v10은 `TP 4 / FP 66 / FN 3`, precision `.057143`, recall `.571429`, F1 `.103896`이었다.
  EXP208에 field replacement하면 `.292959 -> .297288`, 현재 최고 EXP231 composition에
  replacement하면 `.329265 -> .333594`다.
- fast와 holdout에서 보인 recall 회복 방향은 dev200에서도 유지됐지만 precision은 매우
  낮다. 70건을 양성으로 예측해 false positive 66건을 만들었으므로 canonical 승격이나
  submission 사용은 기각한다.
- `PPS-DEV-049`, `PPS-DEV-169`, `PPS-DEV-171`에서 source substring을 반복 생성하는 장문
  이상이 발생했다. 특히 169/171은 completion 8,538/16,569 tokens, latency 85.5/167.7초였고
  malformed pass가 남았다. full catalog와 자유 문자열 review 조합은 evaluator runtime에도
  부적합하다.

결정: 구조화 V-only가 zero-recall absence item을 살릴 수 있다는 방향성 증거로만 보존한다.
다음 EXP250은 schema와 V-only 판정은 그대로 두고 full catalog만 기존 exact-code 기반
조건부 제품 사실로 되돌려, 성능 원인이 구조화 review인지 대형 catalog인지 단일 변수로
분리한다.

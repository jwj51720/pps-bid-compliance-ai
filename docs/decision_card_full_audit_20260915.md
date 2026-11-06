# EXP231 이후 decision card 전수 감사

작성: 2026-09-15, dev / mac

> 2026-09-18 정정: 이 문서의 EXP231 시점 평가는 최신 카드 완결성 결론이 아니다. organizer
> source를 전 항목 동일 기준으로 재감사한 `docs/decision_card_source_concordance_audit_20260918.md`와
> v30 검증 결과 `docs/v30_full_source_concordance_card_plan.md`를 우선한다.

## 목적과 감사 대상

이 문서는 현재 local-quality 최고 조합의 24개 판정 기준을 주최 측 `항목표.json`,
`data/derived/legal_condition_ledger_v1.json`에 보존된 주최 측 법령 원문, 실제 final 입력에서
제공되는 human-readable metadata/제품 사실, 그리고 이미 끝난 item-local 실험 결과와 대조한다.
dev label은 법적 기준을 만드는 데 쓰지 않고, source에서 먼저 찾은 결함이 실제 오류와 같은 방향인지
확인하는 데만 쓴다.

현재 EXP262까지의 최고 `.3537749417`은 하나의 card artifact가 아니다. 이후 v20
corrected-card V-only specialist를 합성한 EXP281은 `.3592573978`이지만, v20만
`TP/FP/FN=5/66/0`이고 전체 topology가 약 1,019 calls라 제출 정책으로 승격할 수 없다.
EXP312 v7 specialist를 runtime상 그나마 덜 나쁜 EXP262 composition에 추가한 새 연구 상한은
`.3746082750`이다. EXP281까지 모두 더한 `.3800907311`은 call/runtime와 v20 precision 때문에
제출 후보가 아니다.

- EXP208 base: `decision_cards_v10_v6_v7_scope.json`
- v4 field replacement: `decision_cards_v11_v4_scope.json`
- v5 field replacement: `decision_cards_v12_v5_threshold.json`
- v14 field replacement: `decision_cards_v16_v14_threshold.json`

따라서 아래의 `effective` 평가는 v4·v5·v14에는 replacement card를, 나머지에는 EXP208의
v10 card를 적용한다. 이 감사는 card를 한꺼번에 바꾸거나 dev별 규칙을 만드는 승인이 아니다.
source-grounded 결함이 가장 강한 한 항목만 별도 config로 검증한다.

## 감사 기준

각 카드에 다음이 명시적으로 있어야 한다.

1. 적용 전제: 계약법, 계약유형, 조달대상, 금액구간 등.
2. 1 조건: 필요한 사실들의 AND/OR 관계와 역할.
3. 핵심 0 조건과 법정 예외.
4. 비교에 필요한 실제 숫자, 기간, 비율 또는 기업범위.
5. final rendered input에서 공급되는 metadata/CSV fact 및 모든 원문과의 연결.

상태는 다음 네 가지를 구분한다.

- `검증됨`: source와 입력이 완결되고 dev200에서도 target 성능이 확인됨.
- `실행 병목`: card/input은 완결됐지만 Gemma가 관계를 안정적으로 적용하지 못함.
- `card 불완전`: source에 있는 필수 조건이 effective card에 빠지거나 모호함.
- `입력 적용성 병목`: card를 더 써도 organizer exact fact가 없는 공고의 적용성을 확정할 수 없음.

## 현재 성능과 항목별 결론

| v | incumbent TP/FP/FN, F1 | 감사 상태 | 결론 |
| --- | --- | --- | --- |
| v1 | `4/1/3`, `.6667` | card 경계 + 실행 병목 | effective card는 특정 기관군 중심이라 조직·상시인력·보유시설 제한을 충분히 말하지 않는다. source-grounded 확장 EXP270은 fast label을 바꾸지 못했으므로 문구만의 문제로 보기도 어렵다. |
| v2 | `7/0/0`, `1.0` | 관찰상 안정, 잠재 card 불완전 | `고시금액 미만`의 숫자 selector가 effective card에 없다. 현재 dev에서는 완벽하지만 v5와 같은 public 취약 가능성이 있어 향후 통합 card에는 실제 임계값과 계약유형 분기를 넣어야 한다. |
| v3 | `8/0/0`, `1.0` | 경계 충돌 재검토 필요 | 항목명은 `1배수 이상`, 국가 시행규칙은 `1배 이내`, 집행기준은 원칙 `1/3배 이내`, 필요 시 최대 `1배`라고 한다. effective card의 `1배를 넘는`은 법령 경계에는 맞지만 항목명과는 등호에서 충돌한다. 현재 성능이 완벽하므로 등호 사례를 source-first로 확인하기 전에는 바꾸지 않는다. |
| v4 | `6/26/0`, `.3158` | source 교정됨, 실행 precision 병목 | item-table의 금액 표현과 별개인 특정기관·특정실적 한정 금지를 source에서 확인해 specialist card로 교정했다. recall은 회복했지만 역할 혼동으로 FP가 많다. 추가 threshold 문구가 아니라 참가자격 실적과 평가·시설·기술 조건의 구분이 병목이다. |
| v5 | `7/4/0`, `.7778` | 비교적 검증됨 | 2.3억/7.1억/지방 분기와 `입찰추정가격` operand를 specialist card에 넣어 recall을 회복했다. 남은 FP는 숫자 비교 실행 오류이며 입력 누락은 아니다. |
| v6 | `0/1/6`, `0` | effective card 불완전 + 관계 실행 병목 | effective card에는 고시금액 숫자 selector가 없다. 이를 보완한 EXP265도 fast positive에서 참가자격 원문을 찾고 0을 냈다. 숫자 보완만으로는 부족하며 기초지역·광역지역·소액수의 허용 관계를 구조화해야 한다. |
| v7 | incumbent `0/0/7`, EXP312 `3/2/4`, `.5000` | attention isolation 이득 + 실행/변동 병목 | v7-only 기존 card가 fast `.6667`, 새 holdout `1.0`, dev200 `.5`로 양성을 회복했다. threshold card와 V-only는 fast labels를 바꾸지 않았다. 과거 byte-identical EXP224 holdout은 F1 0이어서 OpenRouter repeat 변동이 확인됐고, FP는 단일 소재지·납품지를 복수지역 제한으로 오독한 사례다. |
| v8 | `3/3/3`, `.5000` | source 교정됨, 실행 병목 | 평가용 실적·same-bidder AND·지방 소액수의 허용 결합을 명시한 EXP291/292는 fast에서 existing-card와 같은 `1/1/0`이었다. 기존 FP를 고쳤지만 실적제한이 없는 새 공고를 FP로 만들어 순개선이 없었으므로 문구 추가를 중단한다. |
| v9 | `5/8/1`, `.5263` | 실행 precision 병목 | 실제 납품 요구, 배경·기존장비, 동등품, 구체적 필요성의 구분은 card에 있다. FP는 이 역할 구분을 긴 규격에서 실행하지 못하는 문제로 보이며 generic 문구 추가보다 item-local source role 검증이 필요하다. |
| v10 | `0/0/7`, `0` | 입력 적용성 병목 | card의 경쟁제품→직접생산 부재 관계는 맞다. exact-code가 없는 positive의 제품 적용성 fact가 부족하다. full catalog는 recall을 일부 살렸지만 dev200 `4/66/3`으로 과호출했고 runtime도 악화해 기각됐다. |
| v11 | `0/0/6`, `0` | 입력 적용성 + 예외 source 병목 | gold 6건 중 exact-code match는 3건, unknown은 3건이다. current ledger/card는 법 제7조의 `대통령령상 특별한 사유`를 구체적으로 공급하지 않아 예외 범위도 완결되지 않았다. full catalog를 재사용하기 전에 product match와 법정 예외를 각각 보강해야 한다. |
| v12 | `1/1/5`, `.2500` | 입력 적용성 + 논리 실행 병목 | 실제 구매대상↔고시후보↔특이사항↔직생요구 역할을 명시한 EXP298~300은 fast에서 모두 기존 card보다 악화됐다. relation review는 관찰을 맞게 적고도 `경쟁제품적용=적용`과 `카드대조=1조건충족`을 동시에 내는 내부 모순을 보였다. exact-code unknown을 일반제품으로 바꾸거나 schema를 label rule로 쓰지 않는다. |
| v13 | `0/4/6`, `0` | 입력 적용성 + 실행 병목 | structured product/기업범위 review는 fast TP를 살렸지만 independent holdout FP를 늘려 기각됐다. full catalog와 관찰 schema를 더 늘리는 방향은 종료한다. |
| v14 | `5/4/3`, `.5882` | specialist dev200 개선, holdout은 FP 검증만 | 2.3억원, 물품·용역 범위, condition-aware product, 제2조의3 예외를 넣은 card가 fast/dev200에서 개선됐다. holdout에는 양성이 없으며 EXP260→261의 FP 12→0만 확인했다. 동일 card를 all-item에 넣은 EXP263은 v14를 하나도 회복하지 못해 attention/output competition 가능성이 확인됐다. |
| v15 | `0/2/6`, `0` | effective card 불완전 + 실행 병목 | effective card는 실제 고시금액 숫자와 `소기업·소상공인` 대 `중소기업` 경계를 충분히 operationalize하지 않는다. 이를 고친 EXP234는 fast 개선 후 holdout에서 실패했다. source-correct card와 모델 성능을 구분해 보존한다. |
| v16 | `0/0/6`, `0` | card 불완전 + 입력 적용성 병목 | 1억원 상한만 있고 고시금액의 실제 숫자, `중소기업` 제한의 정확한 범위, 제2조의3 예외가 effective card에 구체화돼 있지 않다. absence item이라 제품 적용성과 전 문서 부재를 모두 확정해야 한다. |
| v17 | `0/7/6`, `0` | effective card 경계 오류 + 입력 적용성 병목 | 1억원 미만에서는 원칙적으로 소기업·소상공인 제한이 정상이고, 중기업까지 허용하는 `중소기업` 범위가 문제다. effective card는 이 방향을 명시하지 않는다. corrected EXP237은 FP를 줄였지만 exact-code unknown 때문에 TP를 못 살렸다. |
| v18 | `0/0/7`, `0` | 입력 적용성 + 예외 압축 부족 | 1억원 미만과 소기업 제한 부재라는 기본 관계는 있다. 그러나 일반제품 적용성 unknown과 제2조의3 예외가 병목이며, absence라서 공고 전체의 실제 부재도 확인해야 한다. |
| v19 | `6/9/0`, `.5714` | 관계 실행 병목 확인 | source 역할·시점을 구조화한 EXP285–288에서 V-only가 fast 양성을 회복했지만 negative-only holdout FP가 V/E 1건보다 많은 3건이었다. 모델은 `기타서류`·`입찰마감후`라고 관찰하고도 1을 내므로 카드 문구나 동일 prompt 반복으로 해결하지 않는다. |
| v20 | incumbent `0/0/5`, EXP281 `5/66/0`, `.1316` | card 누락 교정됨, 적용성 실행 병목 | threshold/산식/예외를 보완한 V-only는 양성 5건을 모두 회복했지만 비-SW 공고까지 대량 과호출했다. gate-first EXP282는 fast `1/1/0`으로 좋아졌으나 holdout EXP283에서 `0/0/1`로 양성을 잃었다. 단순 card 강화보다 복합 조달의 실질 SW 역할을 source-only로 분리할 필요가 있다. |
| v21 | `6/0/0`, `1.0` | 관찰상 안정, card 예외 압축 부족 | effective card는 국가 10%·지방 5%만 명시하고 1천억원 이상 공사, 주계약자관리, 20% 범위 조정 등 source 예외를 `별도 확인`으로 남긴다. dev 성능은 완벽하므로 실제 예외 사례 없이 수정하지 않는다. |
| v22 | `5/1/0`, `.9091` | 검증됨 | 협상계약, 설명회 존재, 불참자의 입찰·제안 배제 관계가 명확하고 성능도 안정적이다. |
| v23 | `3/32/2`, `.1500` | source/card 완결, 실행 실패 | 계약법·협상·금액·40/20/10일·긴급/재공고·날짜 역할을 모두 제공했다. EXP273에서는 모델이 국가계약 또는 최소일수 충족을 스스로 기록하고도 전부 1로 냈다. 추가 card 문구나 proof schema를 반복하지 않는다. |
| v24 | `2/7/6`, `.2353` | 입력은 완결, 관계 실행 병목 | 비교 필드와 human-readable counterpart는 모두 입력된다. 같은 필드쌍을 고르는 것과 양립 가능성을 판단하는 단계가 불안정하다. |

## v16 source-concordance 심층 점검

v16은 표면적으로는 card 누락이 크지만, 2026-09-15에 dev200 양성 6건을 원문·metadata·
`competition_products_v1.json`과 다시 대조한 결과 **다음 paid card 후보로는 부적합**하다.

| ID | 제품 fact | 원문상 중소기업 제한/예외 | 감사 결론 |
| --- | --- | --- | --- |
| PPS-DEV-20 | `unknown` | 실제 참가자격에는 없음. `대·중소기업 상생결제`는 참가제한이 아니다. | gold 1과 양립 |
| PPS-DEV-037 | `not_matched` | 제품·면허 자격만 있고 중소기업 제한이 없음 | gold 1과 양립 |
| PPS-DEV-058 | `unknown` | `중소기업 및 소상공인 확인 서류(해당시)`만 있고 참가자격 제한은 아님 | gold 1과 양립 |
| PPS-DEV-065 | `unknown` | 중소기업자 또는 소상공인 및 확인서 보유를 실제 참가자격으로 명시 | gold 1과 표면상 충돌 |
| PPS-DEV-066 | `unknown` | 지역·시설 자격만 있고 중소기업 제한이 없음 | gold 1과 양립 |
| PPS-DEV-067 | `unknown` | 업종·지역 자격만 있고 중소기업 제한이 없음 | gold 1과 양립 |

단순한 문자열 검사는 사용할 수 없다. PPS-DEV-20의 `대·중소기업 상생결제`는 거짓 presence이고,
PPS-DEV-065는 PDF 추출이 심하게 파편화됐지만 참가자격 문장은 복구 가능한 원문으로 남아 있다.
또한 1억~2.3억원 물품·용역 49건 안에는 `unknown + 명시 제한/예외 없음` 조합이 gold positive
3건, gold negative 5건 모두에 존재한다. negative에는 특수기술 metadata, 명시적 제2조의3 예외,
실제 중소기업 확인서, 기관 적용범위 등의 서로 다른 이유가 섞여 있다. 따라서 unknown을 일반제품으로
일괄 승격하거나 제한 문구의 부재를 Python으로 판정하면 안 된다.

현재 card의 결함 자체는 명확하다. 실제 2.3억원 상한, 물품·용역 범위, 제2조의3 예외 목록,
`코드 없음`과 `실제 비경쟁 조달대상`의 구분이 빠져 있다. 그러나 fixed fast20에는 v16 positive가
1건뿐이고 independent holdout20에는 positive가 0건이므로, card를 고쳐 fast에서 1건을 회복해도
규정된 holdout recall 검증을 할 수 없다. PPS-DEV-065의 source/gold 충돌도 해소되지 않았다.
그러므로 v16 card 문안은 source-correct draft로만 남길 수 있고, 별도의 label-blind 적용성 사실이나
독립 양성 검증 cohort 없이 dev200 유료 실행으로 확대하지 않는다.

## 원본 artifact 무결성 확인

2026-09-15에 organizer 배포 archive `/Users/a60157288/Downloads/open (1).zip`을 찾아
`data/항목표.json`을 원본 그대로 복구했다. card에서 역생성하지 않았다.

- 항목표 SHA256: `368cb41f376d8ad7edbbdf181542e6e959de356f7f70d86e72943325ecad61d9`
- dev input SHA256: `7dedfaaf02cc9ea15f4178ed60fc1a4fedf94c37e948a9375edb6557328c6a2b`
- labels SHA256: `84c79302ac190b45b2487ec8e02aab73e59071ee745828e813a7db96d3a97a35`
- 경쟁제품 CSV SHA256: `c372b24e8e4878ca5d8b9c729acb968d243abfe2a8099c32c944eb398a4f3bfe`

네 파일은 archive member와 exact hash가 일치한다. 24개 item과 5개 absence item을 로드했고,
현재 24개 decision-card artifact에 기록된 `source_item_table_sha256`도 모두 복구한 항목표와
일치한다. 새 run의 `run_meta.json`에는 항목표 경로와 hash도 기록한다. 따라서 현재 card 감사의
제약은 원본 누락이 아니라 card 의미 충실도와 모델 실행 성능이다.

## 가장 중요한 결론

v9 후속:051 fixed-fast 양성의 전체624행을 재독했지만 특정 제조사/모델은 확인되지 않고
generic C-ARM 및 규격서 참조만 존재한다. Raw organizer도D0뿐이며 local drop은 없다.
이는 gold error 확정이 아니라 source/annotation 불확실성이다. v9 source-role schema도
기존 card/navigation으로 표현할 수 있어 필요성이 입증되지 않았다. EXP319/320
attention/output안은 유료 전 invalidated했고 결과로 세지 않는다.
상세`docs/exp319_exp320_v9_attention_output_plan.md`.

v24 후속 감사에서 검증 수준을 좁혔다. supplied input 전달은 검증됐지만8개 positive 중
049/062는 organizer 네 비교축만으로 설명되지 않고 fixed holdout positive는0이다.
두 공고의 raw/normalized source는 모두 D0만 있어 local attachment-drop은 확인되지 않았다.
card의 `제한 문구만`0 조건도 명시 metadataN과의 모순을 면제하는 뜻으로 읽히면 안 된다.
이는 잠재 모호성이지 성능 원인으로 입증된 수정 가설이 아니다. 이미 기각된 role-pair
구조를 반복하지 않으며 `docs/v24_source_concordance_recheck_20260915.md`에 exact audit 기록.

1. 현재 문제는 단일 원인이 아니다. `card 자체 결함`, `organizer applicability fact 부족`,
   `Gemma 관계 실행 실패`, `all-item attention 경쟁`이 동시에 존재한다.
2. semantic-input audit의 PASS는 card 문자열·metadata·문서가 렌더됐다는 뜻이지, card가 법령의
   수치와 예외를 충분히 압축했다는 뜻이 아니다. 앞으로 두 감사를 분리한다.
3. 카드 전수 수정은 허용하지 않는다. 여러 항목을 한 artifact에서 바꾼 과거 v5 calibration은
   원인 분리를 깨고 성능이 하락했다.
4. V-only는 v4·v5·v6·v1에서 V/E와 동률이고 v10 반복검증·v23 proof에서는 열위였다. 카드가
   불완전한 상태에서 호출을 반복해도 같은 불완전한 기준을 반복 적용할 뿐이다.
5. relation schema가 source 사실을 올바르게 구조화해도 그 자체로 논리 실행이 보장되지 않는다.
   EXP299/300에서 Gemma는 자신의 `경쟁제품적용=적용`, `직접생산요구역할=없음` 관찰과 모순되는
   `1조건충족` 또는 최종 1을 냈다. schema field를 Python AND rule로 바꾸는 것은 금지한다.
6. temperature 0도 provider repeat 동일성을 보장하지 않는다. byte-identical v7 holdout prompt가
   EXP224에서는 0, EXP309에서는 1을 냈다. 단일 repeat의 개선을 새로운 independent evidence로
   세거나 best-of-run을 선택하면 안 된다.

## 다음 실험 우선순위

### 완료되어 더 반복하지 않을 후보

- v20 corrected-card V-only는 fast/holdout/dev200에서 recall을 회복했지만 dev200
  `TP/FP/FN=5/66/0`으로 적용성 precision이 붕괴했다. stronger gate는 holdout positive를 잃었다.
- v19 role proof는 관찰을 맞게 기록하고도 잘못된 1을 냈고 V-only holdout FP가 더 많았다.
- v8 operational card는 fast에서 기존 card와 동률이고 FP identity만 바뀌었다.

따라서 이 세 family의 card 재문구·동일 prompt 반복·V-only consensus는 중단한다.

### 1. organizer 원본과 local 실행 무결성 복구 — 완료

위 hash 대조와 24개 card provenance 검증을 완료했다.

### 2. v12의 `실제 구매대상 ↔ 직접생산 대상 코드` 관계 감사 — 완료·기각

v12 양성 6건 중 세 건은 현재 index가 문서 안 exact code를 찾아 `matched`로 표시한다. 그러나
원문 대조 결과 그 code가 실제 계약목적물과 같은지, 또는 참가자격에 잘못 붙인 별도 서비스인지,
그리고 CSV `특이사항`이 금액·SW 조건상 실제 적용되는지가 핵심이다.

- PPS-DEV-053은 실제 계약목적물이 위탁연구인데 행사기획 서비스 code의 직접생산을 요구한다.
- PPS-DEV-054는 축제대행 code가 실제 목적물과 같지만 CSV 조건은 `추정가격 3억원 미만`이고
  실제 추정가격은 약 3.27억원이다.
- PPS-DEV-056은 실제 목적물에 가까운 인터넷지원개발서비스 code지만 CSV 특이사항이
  `소프트웨어 진흥법 제48조 적용`이다.

이 세 유형은 단순 exact-code presence가 곧 적용제품이라는 전제를 반증한다. 기존 7-category
navigation은 관련 문구를 찾을 수 있어도 `실제 구매대상`, `직접생산 요구 대상`, `CSV 조건 충족`
사이의 관계를 명시적으로 보존하지 않는다. 따라서 다음 후보는 v10-v18 전체 schema가 아니라
v12 하나에서만 이 관계가 기존 final에 전달될 때 label이 개선되는지 확인한다. fixed fast20과
independent holdout20에 각각 v12 positive가 1건 있어 사전 gate도 가능하다.

비교 결과는 다음과 같다.

- EXP297 existing-card V/E: fast v12 `TP/FP/FN=1/1/0`, F1 `.6667`.
- EXP298 source-correct card plain V/E: `0/2/1`, F1 `0`.
- EXP299 relation review V/E: `0/3/1`, F1 `0`.
- EXP300 relation review V-only: `0/7/1`, F1 `0`.

네 arm 모두 20건, parse error 0이고, exact tokenizer source omission도 0이다. EXP299/300은 관계
관찰을 맞게 적은 사례에서도 최종 논리를 거꾸로 적용했다. 승격 조건을 충족한 arm이 없으므로
EXP301~305 holdout/dev200/evidence recovery는 실행하지 않는다. 이 family를 더 긴 card, enum 추가,
동일 prompt 반복으로 보정하지 않는다.

### 3. 다음 card 후보 선정 방식

남은 항목을 card 문구가 빈 순서로 고르지 않는다. 각 항목마다 먼저 다음 세 조건을 동시에 요구한다.

1. organizer 항목표/법령 provenance에서 incumbent card의 누락 또는 경계 오류가 exact span으로
   입증될 것.
2. 그 누락이 실제 incumbent FN/FP를 설명하고, source/gold 충돌이 아닐 것.
3. fixed fast와 independent holdout에 최소 한 개씩 informative positive/negative가 있어 card 효과와
   우연한 label 이동을 분리할 수 있을 것.

이 gate를 통과하지 않는 항목은 source-correct draft만 남기고 paid run을 하지 않는다. 통과하는
최소 한 항목에서 existing-card V/E → card-only V/E → 필요한 경우에만 source-role review/V-only
순서로 비교한다.

### 중단 항목

- v23 proof/checklist/date-navigation 재문구
- v10/v13 full product catalog
- 같은 prompt의 반복 V-only consensus/majority
- 여러 card를 한 번에 교정하는 bundle
- v19 서류종류×행위×시점 role-proof 및 그 V-only 반복: fast `1/1/0`이었지만 holdout
  `0/3/0`으로 일반화 실패
- v8 operational card/V-only: source-correct 경계를 넣어도 fast existing-card와 `1/1/0` 동률이고
  FP identity만 바뀌어 holdout 진입 실패

## 제출과의 관계

## 추가 source-concordance: 서로 다른 예외 체계의 누락

2026-09-15 재점검에서 기존 ledger 요약만으로는 예외 완결성을 검증할 수 없음을 확인했다.
아래는 주최 측 배포 TXT를 직접 읽은 결과다. 현재 법률의 일반적인 해석을 외부에서 보충한
것이 아니라, 대회 제공 source와 effective card의 차이를 기록한다. canonical card/runtime는
변경하지 않았다. v18만 별도 실험용 카드로 구현했으며 이 발견 자체를 성능 개선으로 보고하지 않는다.

| 항목 | organizer source와 exact anchor | effective card 차이 | 후속 검증 범위 |
| --- | --- | --- | --- |
| v11 | 판로지원법 시행령 제7조 제1항: `우선구매 대상으로 규정한`, `조합이 추천한`, `적격자가 없는 등의 사유로 유찰`, `특정한 기술ㆍ용역이 필요한 경우`; 제2항: `그 사유를 입찰공고문에 기재하거나` 전자조달시스템에 입력 | 카드에는 적용제품과 중소기업 제한 부재만 있고, 이 네 예외와 예외사유의 공고/메타 입력 경로가 없다. ledger도 법 제7조만 연결한다. | 예외를 일반 제2조의3과 섞지 말고 v11 하나에서 압축한다. 메타에 실제 예외사유가 공급되는지도 별도 확인해야 한다. 예외 추가는 주로 FP 억제 가설이지 unknown-product FN 회복 가설이 아니다. |
| v13 | 판로지원법 제7조의2 제1항: `중소벤처기업부장관이 지정한 물품 또는 용역`; 제2항: `셋 이상의 소기업 또는 소상공인이 조합과 함께` 공동사업을 하여 제품화, 공동사업 참여기업 제한 또는 조합 추천 지명경쟁 | 카드의 `별도 허용 사유`에는 지정품목·공동사업의 실체가 없다. ledger의 법 제7조만으로 이 예외를 추적할 수 없다. | 지정품목 fact가 organizer source에 존재하는지 먼저 확인한다. 일반 경쟁제품 index가 이 별도 지정을 자동 증명한다고 취급하지 않는다. 기각된 full-catalog/review를 재실행할 이유는 아니다. |
| v17 | 판로지원법 시행령 제2조의2 제1항 제1호 단서: 소기업·소상공인 `3인 이하임이 명백` 또는 `2인 미만`/적격자 없는 유찰이면 중소기업자간 제한경쟁 가능 | effective card는 중소기업·소기업·소상공인을 한 묶음으로 두고 `유찰 등 예외`라고만 쓴다. 정상 소기업 제한과 예외적 중기업 허용의 방향이 불명확하다. | EXP237의 방향 교정과 이 두 단서의 포함 여부를 구분한다. 새 실행 전 기존 card와 corrected card의 exact 차이를 확인한다. |
| v15/v16/v18 | 판로지원법 시행령 제2조의3 제1항: 유찰, 특정 비영리법인 참여 필요 용역, 다른 법령 우선구매/수의/지명 근거, 특정 성능·기술·품질로 우선조달 불가능, 장관 고시 준하는 경우; 제2항 공고/시스템 사유 입력 | `판로지원 예외`라는 이름만으로는 용역 유형·필요성·실제 적용과 단순 비영리 참여 허용을 구분할 수 없다. | 예외 존재와 기업규모 제한의 실제 제거를 원문에서 구분한다. 단순 연구용역/특수기술 단어를 예외 label rule로 사용하지 않는다. |

위 조문은 `data/raw/open/data/법령패키지/법령/` 아래 파일명 NFC 표기 기준
`중소기업제품 구매촉진 및 판로지원에 관한 법률.txt`(제7조의2, 실제 파일 63–68행),
동명 `시행령.txt`(제7조, 실제 파일 118–125행)에서 확인했다. mac 파일명은 NFD이므로
reproduction 시 파일명 normalize 또는 source hash로 식별한다. 제2조의2/제2조의3 원문은
ledger의 `sme_decree_2조의2`, `sme_decree_2조의3` exact chunks와도 대조했다.

### 감사 완료 상태를 과장하지 않는 기준

### Product-item source packet과 cohort gate 재검증

`scripts/audit_product_item_sources.py`를 실행해 관련 양성 공고의 모든 문서·metadata·exact-code
fact를 변경 없이 offline review packet으로 내보냈다. 원문/내부 status를 포함하는 이 packet은
감사용이며 model prompt로 주입하지 않는다. 결과는
`outputs/product-item-source-audit-20260915/report.json`과 ID별 Markdown이다.
법적 label을 계산하거나 keyword로 문서를 제외하지 않는다.

| item | gold positive | lookup matched / not_matched / unknown | fast / holdout positive |
| --- | --- | --- | --- |
| v11 | 6 | 3 / 0 / 3 | 1 / 0 |
| v13 | 6 | 4 / 0 / 2 | 1 / 0 |
| v16 | 6 | 0 / 1 / 5 | 1 / 0 |
| v17 | 6 | 1 / 3 / 2 | 1 / 1 |
| v18 | 7 | 0 / 2 / 5 | 1 / 1 |

이 결과의 `matched`는 CSV exact code presence이며 실제 구매대상에 대한 적용 확정이 아니다.
PPS-DEV-053(v17 holdout)은 학술연구라는 목적물에 행사 관련 직접생산 code가 붙은 사례다.
이는 이미 v12 source audit에서 확인한 target/code mismatch와 같은 사례이므로 별도의 독립
evidence로 세지 않는다. PPS-DEV-042(v17 fast)는 실제 참가자격에 중·소기업을 포함하는 확인서를
요구하며 원문의 법조 참조와 기업범위 문구가 일치하지 않는다. 법조 번호만으로 기업범위를
확정하지 않는다.

v18 holdout PPS-DEV-044의 공고 앞부분에는 참가자격 section의 소기업 제한이 없어도 제출서류에
소기업·소상공인 확인서가 있다. 이는 `확인서가 어딘가 존재함`과 `실제 참가자격으로 제한함`의
구분이 필요한 사례다. 이후 2,040행 전체(D0 공고문/D1 제안요청서)를 읽었다. 첨부 참가자격은
공고문을 참조하고 있으며, 공고 제출서류의 확인서 요구를 없애거나 예외화하지 않는다.
그러므로 자격제한의 실질을 둘러싼 ambiguity는 남아 있고 source/gold conflict로 단정하지 않는다.
이 경계를 임의로 해결하지 않는 최소 비교 계획은
`docs/exp314_exp316_v18_absence_card_plan.md`에 기록했다. 아직 card/config 구현과 paid gate는
완료되지 않았으며 실험 결과는 없다. 이후 checkpoint에서 v18 실험용 카드와 EXP314–316
config 구현, 최종 카드 fast20 admission 및 mock을 완료했다. 유료 실행 전 rendered/source
contract 검토가 남아 있으며 canonical 정책은 그대로다.

후속 최종 checkpoint: EXP314–318 fast/holdout까지 완료, v18 corrected-card 승격 기각.
기존/교정 V/E holdout은 `1/4/0` F1 `.333333`과 `1/11/0` F1 `.153846`이다.
교정 V-only fast는 `0/4/1` F1 0. 원문 제한 존재(194)와 금액초과(032)를 무시한1은
한pass raw label이므로 merge 누수가 아니다. 이 family 재문구/repeat/dev200 중단.
자세한 source-fidelity 개선과 성능 실패는 `docs/exp314_exp316_v18_absence_card_plan.md`.

따라서 v11/v13/v16의 새 recall candidate는 기존 holdout에서 recall을 검증했다고 보고하면
안 된다. 기존 panel은 유지하며 독립 positive validation 설계를 먼저 문서화해야 한다.
v17/v18은 panel gate가 가능하지만 적용대상·제한 역할을 source에서 먼저 확정해야 하므로
카드 예외 추가만의 paid run은 아직 시작하지 않는다.

- 원본 파일 무결성, card asset 선택/렌더링, 법적 의미 완결성, 실제 모델 실행 성능은 서로 다른
  검사다. 앞의 두 검사가 PASS여도 뒤의 두 검사가 PASS인 것은 아니다.
- 이 문서의 24-item 표는 1차 진단이다. 모든 조건을 source exact span과 실제 rendered span으로
  연결한 최종 전수 증명표는 아직 완료되지 않았다.
- gold evidence 전수 대조에서 비어 있지 않은 54개 양성 근거는 모두 제공 원문의 한 문서에
  exact substring으로 존재했다. 하지만 비-absence 양성 68개는 gold evidence가 비어 있어
  이 검사만으로 판단 근거의 완결성을 증명할 수 없다. 고정 holdout에는
  v6/v8/v11/v13/v14/v16/v19/v21/v24 양성이 없다. 상세 범위와 한계는
  `docs/dev_evidence_observability_audit_20260915.md`에 기록했다.
- 다음 paid 후보는 누락 조문을 모두 한 번에 넣는 bundle이 아니다. 가장 작은 source-proven
  item 하나의 card-only 변경을 선언하고, source/metadata/제품 적용성이 충분한 사례에서
  existing-card V/E와 비교한다. 그 뒤에만 V-only/추가 pass를 검토한다.
- absence merge는 전 문서의 restriction presence를 결합하는 논리다. applicability unknown과
  실제 restriction absence를 같은 0/1로 숨기면 보수적 AND가 FN을 만들 수 있다. 이 가능성은
  실제 pass별 출력으로 검증해야 하며, 여기서는 merge 변경을 승인하거나 구현하지 않았다.

이 감사는 `.353775`의 819-call local-quality 조합을 바로 제출 가능하게 만들지 않는다. 현재
EXP231 제출은 619-call V/E 구조로 120분을 초과했고, v14까지 더하면 runtime 위험이 더 크다.
먼저 source-correct item policy로 local quality를 높인 뒤, 검증된 항목들을 한 호출에서 잃지 않는
새 topology를 별도 실험해야 한다. batch size는 총 생성량이나 호출 수를 줄이지 않는다.

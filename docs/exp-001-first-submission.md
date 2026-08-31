# EXP-001 — First Submission Baseline 결과

## 목적과 범위

공식 dev 200건을 대상으로 데이터 로딩부터 Gemma 호출, 49열 제출 파일 생성, 검증, 로컬 평가까지 하나의 파이프라인으로 관통했다. 이번 실험은 RAG, self-label, 규칙 보정을 사용하지 않은 기준선이다. 사용자 지정 종료 범위에 따라 test simulation과 DACON 제출은 후속 작업으로 남긴다.

## 설정과 재현

- 입력: `data/raw/open/dev.jsonl.gz` (200건)
- 정답: `data/raw/open/dev_labels.csv`
- 모델: `google/gemma-4-26b-a4b-it` via OpenRouter
- 프롬프트 입력: 공고당 문서 최대 4,000자
- 생성: temperature 0, max tokens 2,500, seed 20260826
- 실행: 동시성 4, JSON Schema structured output, 체크포인트 재개
- 파생 데이터: 없음

```bash
source .venv/bin/activate
python scripts/profile_data.py --config configs/config.exp001-first-submission.yaml
python scripts/run_experiment.py --config configs/config.exp001-first-submission.yaml
python -m pytest -q
```

정확한 설정, 입력·정답·소스 SHA-256 및 run signature는 `outputs/exp-001-first-submission/run_meta.json`에 있다.

## 결과

| 지표 | 결과 |
|---|---:|
| Local dev macro F1 | 0.220416 |
| Evidence validity | 0.795082 (244건) |
| Evidence span F1 | 0.322106 (54건) |
| Evidence exact match | 0.055556 |
| 성공 응답 토큰 | 908,257 |
| 성공 응답 보고 비용 | $0.1221054 |
| 응답 지연 중앙값 / P90 | 7.906초 / 9.923초 |

제출 검증은 200행, 49열, 고유 ID, 이진값 조건을 통과했다. 전체 실행은 402 응답으로 두 번 재개되어 최초 full-run 시작부터 완료까지 약 508초가 걸렸다. `run_meta.json`의 52.876초는 마지막 재개 구간만 나타낸다. 실패 시점의 402 이력은 `failed_responses.jsonl`에 보존했다.

항목별 최고 F1은 v22 0.8889, v3 0.6087, v1·v19 0.5714였다. v10, v11, v12, v14~v18, v20은 F1 0이었다. v13은 112건, v24는 34건을 positive로 예측해 과탐지가 컸고, 유효 근거문 없는 positive 경고 50건도 주로 이 두 항목에 집중됐다.

## 후속 진단

### 출력은 잘리지 않았다

200개 raw response가 모두 24항목 JSON으로 파싱됐다. completion은 평균 676.56토큰, 최대 931토큰으로 2,500토큰 한도의 37.24%에 불과하다. 따라서 낮은 점수의 원인을 출력 truncation으로 볼 근거는 없다. 이후 실행부터는 OpenRouter의 `finish_reason`도 checkpoint에 저장한다.

### 입력 truncation은 존재하지만 주원인은 아니다

제공된 모든 문서가 4,000자 context에 온전히 들어간 공고는 8/200건뿐이다. 정답 근거가 있는 non-absence positive 54건 중 47건(87.04%)은 근거가 실제 모델 입력에 있었다. 그러나 이 47건의 positive recall은 44.68%였다. 숨겨진 근거 7건은 모두 놓쳤으므로 문서 선택 개선은 필요하지만, 보이는 근거도 절반 이상 판정하지 못했다는 점에서 주원인은 항목별 판정 조건 부족이다.

특히 v13은 일반적인 소기업·소상공인 참가자격 문구를 `중기간 경쟁제품` 여부 확인 없이 위반으로 처리해 108 FP를 만들었다. 반대로 금액·제품 분류·예외 조건이 필요한 v10~v18 다수는 거의 positive를 출력하지 않았다. 현재 prompt는 항목명과 비고만 제공하며, 서로 유사한 항목을 구분하는 명시적 decision boundary가 없다.

유효 근거문이 있는 positive의 precision도 20.10%에 그쳤다. 원문 substring이 존재한다는 사실은 그 문장이 해당 위반이라는 뜻이 아니다. 근거가 없는 positive를 모두 0으로 바꾸는 counterfactual은 macro F1을 0.220416에서 0.219384로 낮췄으므로 evidence hard gate는 사용하지 않는다.

### 판정과 근거 생성 구조

현재는 Gemma가 24개 판정과 근거 후보를 한 번에 생성하고, Python이 후보를 exact substring으로 복원·검증한다. 즉 근거 검증은 이미 분리되어 있지만 LLM 생성 계약은 결합되어 있다. 공고당 복수 Gemma 호출은 금지되지 않으나 test 1,853건과 2시간 제한 때문에 모든 항목별 호출은 부적절하다.

다음 비교 실험은 다음 두 구조를 같은 표본에서 평가해야 한다.

1. 24개 판정만 생성한 뒤 Python evidence engine 실행
2. 현재처럼 판정과 근거 후보를 함께 생성

필요하면 ambiguous case 또는 근거가 없는 positive에만 선택적 second pass를 적용한다. free provider 429로 판정 전용 ablation의 세 시도가 모두 실패했으므로, 분리가 점수를 높인다는 결론은 아직 내리지 않는다.

### OpenRouter free smoke

기본 모델을 `google/gemma-4-26b-a4b-it:free`로 변경했다. 무료 endpoint는 `provider.require_parameters=true`일 때 404가 발생해 이를 설정 가능한 값으로 만들고 false로 지정했다. strict JSON Schema 요청 자체는 provider까지 전달된다.

동일한 앞 5건 smoke 결과는 1건 성공, 4건 429 retry 소진이었다. 성공한 PPS-DEV-01은 기존 유료 결과와 24/24 label 및 24/24 evidence가 같았다. PPS-DEV-03에서는 nested schema 대신 flat JSON이 한 번 반환됐으며 보수적으로 읽으면 기존 결과와 23/24 label이 같았지만, 제출 가능한 응답이 아니므로 폐기했다. 같은 모델 계열이라는 정황은 있으나 품질 동등성은 검증되지 않았다. 현재 성공률로 200건 전체 실행은 진행하지 않는다.

누적 충전액 $10을 확인한 뒤, 모든 항목의 positive를 2~3건씩 포함하도록 선택한 30건 stress sample도 실행했다. 무료 요청만 사용했으며, 그중 정상 checkpoint된 5건은 기존 유료 baseline과 label 120/120이 일치했고 evidence는 119/120이 일치했다. 이는 동일한 prompt·seed에서 강한 동작 일치 신호이지만, 성공 표본이 5건뿐이므로 품질 동등성 또는 local F1 동등성을 결론 내리기에는 부족하다. 30건 모두의 성공 paired output이 쌓이기 전에는 full dev run을 시작하지 않는다.

무료 모델의 운영 조건은 유료 모델과 다르다. 무료 variant는 Google AI Studio 단일 endpoint이며, paid variant는 여러 provider 중 하나로 라우팅된다. 양쪽 요청의 prompt, temperature 0, seed, max tokens 2,500, JSON Schema는 같지만 free endpoint에서는 `provider.require_parameters=false`가 필요하다. `true`일 때는 404가 발생했다. 이후 free endpoint는 `upstream_provider_shared_pool`의 429를 반환했고, 명시적으로 `free-models-per-min` rate limit도 관측됐다. OpenRouter 계정의 누적 크레딧은 $10으로 확인됐으므로 이것은 일일 request cap이 아니라 Google AI Studio 공유 upstream pool의 일시 제한이다.

재현 명령은 다음과 같다.

```bash
python scripts/diagnose_experiment.py
python scripts/run_experiment.py --config configs/config.free-smoke.yaml --limit 5 --fresh
python scripts/select_equivalence_sample.py
python scripts/run_experiment.py --config configs/config.free-equivalence.yaml --ids-file outputs/exp-001-free-equivalence/sample_ids.json
```

## 결론과 다음 실험

EXP-001의 로컬 범위는 성공했다. 다음 실험의 첫 우선순위는 항목별 판정 조건, 특히 v12~v18의 제품 분류·금액·예외 계층과 v24의 field-by-field 비교를 명시하는 것이다. 그 다음 평가 모델의 32,768-token sequence budget(출력 예약분 포함) 안에서 모든 문서 유형과 metadata를 보존하는 token-budgeted selector를 비교한다. 베이스라인의 16,384-token 설정은 실행시간을 위한 예시일 뿐 평가 상한이 아니다. 판정 전용/결합 출력 비교는 free endpoint가 안정된 뒤 같은 표본으로 수행한다.

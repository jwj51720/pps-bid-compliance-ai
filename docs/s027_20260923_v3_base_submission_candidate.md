# S027 — 2026-09-23 신규 제출 후보: v3 specialist 제거

제출 ZIP: `dist/pps_20260923_163852.zip`
SHA-256: `2c6a7ba69d2f2a5cfac067acfb06acb2fc217bbfa57d2ce044d43737ac8b9fe1`

## 선택 이유와 실제 변경

전날 public 0.6053527995를 받은 S001과 **다른 판정 정책**이다. S001의
dev-adaptive v3 specialist task/최종 owner만 제거하고, 원래 r10의 v3 판정을
사용한다. v1·v2·v4~v24, 카드/제품 fact, v19 specialist, BGE, 출력/evidence,
batch 128, invalid 최대 2회 재시도는 그대로다. 공식 지역제한 금액 보정과
실패한 S026 역할 gate는 넣지 않았다. ZIP 내부 변경 파일은 `script.py`와
`runtime_config.json` 두 개뿐이며, 단순 재포장이 아니다.

S005 `experiments/manifests/clean_exp_s005_v3_revert_ablation_v1.json`에서
base S001·허용 정책 차이를 선언하고 preflight PASS를 확인했다. ZIP 생성은
`scripts/package_s027_v3_base_submission.py`, exact archive replay는
`scripts/audit_s027_archive_parity.py`로 재현한다.

## 검증 결과

| 지표 | 전날 S001 | 오늘 S027 |
|---|---:|---:|
| dev200 Macro positive-F1 | 0.8151465658 | 0.7910823947 |
| fast20 | 0.7277777778 | 0.7069444444 |
| holdout20 (재사용 dev 일부) | 0.4305555556 | 0.3888888889 |
| dev200 initial logical calls | 661 | 600 |
| dev200 저장응답 포함 총 호출 | 683 | 620 |

dev200에서 v3 8개 V셀·e3 10개 셀이 달라졌고 나머지 v/e는 동일하다.
S027 ZIP 자체의 저장응답 replay는 200건/49열에서 S005 반사실 CSV와
cell difference 0이었다. 출력은
`outputs/clean-exp-s027-v3-base-archive-parity-v1/`에 보존했다.
동일 응답에서는 base 435, v19 specialist 165의 initial 600 tasks와
retry 18, v19 fallback B 2로 총 620 requests였다. batch 128은 이
logical call 수를 줄이지 않는다. S001과 동일한 base notice 구성에서 v3
specialist 61개만 빠졌으므로 source-document context 선택은 변경되지 않는다.

ZIP exact staged mock 10건 PASS. 생성된 dev CSV는 200개 고유 ID,
정확한 순서의 49열, v1~v24 정수형 0/1, NFC·500자 이하 evidence를 확인했다.
S005 반사실 실행은 evidence cleaner를 통과했다. ZIP 멤버 14개,
압축 153,130 bytes이며 패키지 script의 금지된 유래 표현은 0건이었다.
전체 pytest는 242 passed.

## 제출 판단과 한계

### S028 신규 Gemma 응답 dev200 (2026-09-23 추가)

사용자 지적에 따라 저장응답 replay와 분리해 **S027 ZIP의 `script.run`을
OpenRouter Gemma 4 26B A4B IT 신규 응답으로 다시 실행**했다. BGE ranking은
입력·embedding 정책이 불변이므로 기존 저장값을 재사용했다. 실행·응답
checkpoint·CSV·per-item confusion은
`outputs/clean-exp-s028-s027-fresh-dev200-v1/`에 있다.

- dev200 Macro positive-F1 **0.7894287115**; fast20 0.7325126263;
  holdout20 0.4305555556. 저장응답 replay 0.7910823947과는 구별한다.
- 신규 API 호출 639 = initial 600 + invalid retry 37 + v19 fallback B 2.
  전송 실패 0, remote 경과 954.80초. batch 128.
- 출력 200건·49열·고유 ID·binary labels·500자 이하 원문 substring evidence
  검사 PASS. 비어 있지 않은 invalid evidence 0.
- invalid 2회 재시도 뒤에도 C24 14 tasks가 unresolved였다. 제출 코드는
  이 경우 다른 정상 결과를 유지하고 유효 CSV를 출력한다. 이는 출력 실패는
  아니지만 v24의 불안정성 및 정확도 위험이다. fresh v24 TP/FP/FN=7/44/1.
- 이것은 **새 모델 응답으로 측정한 로컬 점수**다. evaluator vLLM/public 점수와
  동일하다고 주장하지 않는다. remote 954.80초도 evaluator 실행시간 근거가 아니다.

이는 **오늘 제출 가능한 신규 정책 ZIP**이지만 public 성능 개선을 보장하지
않는다. local/dev200 점수는 0.02406 낮다. 선택 목적은 dev에 농축된 v3
specialist의 public 효과를 한 변경으로 분리하고, 120분 제한에 대한 호출
부담을 줄이는 것이다. 직전 동일 기본 runtime은 evaluator에서 95분 27초에
완주했지만 S027 자체의 vLLM 시간은 측정하지 못했다. 저장응답 replay는
출력 조립·패키지 동등성 검증이지 새로운 Gemma 생성 성능 검증이 아니다.
비라벨 20k 역할/분포 감사는 과적합 위험 신호일 뿐 public 정답을 제공하지
않는다. public 결과가 나오기 전에는 S027이 S001보다 낫다고 주장하지 않는다.

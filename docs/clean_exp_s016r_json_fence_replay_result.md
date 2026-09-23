# S016R — v19 repeat JSON fence 0-call replay 결과

실행일: 2026-09-23

상태: **PASS — 사전 고정 repeat gate 통과, adaptive dev diagnostic 한계 유지**

## 무결성

- LLM calls: 0
- embedding calls: 0
- raw S016 response 8건 재사용
- exact single outer fence recovered: 사전 고정 6/6
- raw JSON response unchanged: 2/2
- fence 내부 JSON object structural equality: 6/6
- semantic valid repeat: 10/10
- prompt/schema/reducer/evidence/selected task: 변경 없음
- manifest undeclared differences: 0
- output:
  `outputs/clean-exp-s016r-v19-json-fence-replay-v1/run_report.json`

## 품질 결과

| metric | primary | positive-repeat consensus | delta |
|---|---:|---:|---:|
| v19 TP | 6 | 6 | 0 |
| v19 FP | 4 | 2 | -2 |
| v19 FN | 0 | 0 | 0 |
| v19 precision | 0.6000 | 0.7500 | +0.1500 |
| v19 recall | 1.0000 | 1.0000 | 0 |
| v19 F1 | 0.7500 | **0.8571428571** | +0.1071428571 |
| dev200 Macro | 0.8151465658 | **0.8196108515** | +0.0044642857 |

repeat가 제거한 FP는 `PPS-DEV-051`, `PPS-DEV-098`이다. TP 6건은 모두 repeat에서도
positive였다. FP `PPS-DEV-162`, `PPS-DEV-190`은 repeat에서도 positive라 남았다.

사전 gate 네 조건은 모두 통과했다.

1. all semantic valid: PASS
2. TP repeat-positive >=5/6: 실제 6/6, PASS
3. FP repeat-positive <=3/4: 실제 2/4, PASS
4. v19 F1 >0.75: 실제 0.8571, PASS

## 일반화·효과 크기 판단

이 결과는 모델의 독립 생성 확인이 불안정 FP를 줄일 수 있다는 구조적 증거다. 하지만 selected
10건과 gate 모두 반복적으로 본 dev200을 사용했으므로 public precision 개선률의 추정치가 아니다.
특히 표본은 TP 6, FP 4뿐이라 `FP 2개 제거`의 불확실성이 매우 크다.

또한 전체 macro 증가는 `+0.00446`에 불과하다. public-local gap 약 `0.20979`의 2.13% 크기이며,
상위권과의 public gap `0.14465~0.17465`를 설명하지 못한다. 이 전략을 전체 원인 해결책으로
과장하지 않는다.

## runtime 판단

dev native candidate positive rate `10/165=6.06%`와 S012의 test native task 추정치
`1410.133`을 결합하면 추가 test call은 약 `85.46`개다. 더 중요한 점은 첫 wave 결과 뒤에만
positive를 알 수 있으므로 두 번째 순차 wave가 필요하다는 것이다. 현 제출 runtime 95분 27초에
대해 24분 33초 여유만 있으므로 evaluator vLLM 계측 없이 canonical submission에 넣지 않는다.

## 결론

- 유지: typed v19 owner/reducer와 repeat-confirmation 연구 방향
- 즉시 제출 통합: 보류
- 이유: adaptive dev, macro 효과 작음, sequential runtime 위험
- 다음 진단: public gap 대부분을 담당하는 base r10/B/C24의 hash-fixed exact-repeat panel
- JSON fence adapter는 label 불변 parser hardening 후보로 별도 유지한다.

# N003 v1 restriction-axis fast20 result

작성일: 2026-09-22

결론: **구조는 개선됐지만 승격 보류.** strict 결과는 TP=3, FP=1,
FN=0, U=2, invalid=2, F1(U→0)=`0.8571428571`이다. 사전 gate의
invalid=0을 통과하지 못했고, raw axis를 의미대로 투영하면 invalid
두 건 중 하나가 FP가 되어 TP=3/FP=2/FN=0, F1=`0.75`다.
holdout/dev200은 실행하지 않는다.

| fast20 v1 | TP | FP | FN | U/invalid | 진단 F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| N001 direct state | 0 | 0 | 3 | 20/20 | 0.000000 |
| N002 explicit state | 3 | 4 | 0 | 1/1 | 0.600000 |
| N003 typed axes, strict | **3** | **1** | **0** | **2/2** | **0.857143** |
| N003 raw semantic projection | **3** | **2** | **0** | 0 | **0.750000** |

N002의 실적·지역 FP 네 건 중 PPS-DEV-062(실적), 042(지역),
039(지역)은 target=N 또는 strict U로 줄었다. 그러나 다음 관계
오류가 남았다.

- PPS-DEV-051: “대학병원에 납품한 실적”에서 대학병원은 입찰자의
  기관 유형이 아니라 과거 납품 상대인데 target=Y로 오판했다.
- PPS-DEV-039: 소기업·소상공인 제한을 target=Y로 오판했고,
  quote의 공백을 정규화해 exact substring 검증도 실패했다. raw
  `target=Y, allowed=N`이므로 quote를 복원해도 FP다.
- PPS-DEV-32: 법정 등록 제한을 `target=Y, allowed=Y`로 관측했다.
  최종 의미는 정상 N이지만 모델 quote가 OCR 순서를 바꿔 exact
  검증 실패했다. final positive가 아니므로 evidence 필요성 자체를
  별도 reducer 정책으로 검토할 수 있으나, 이를 고쳐도 위 FP는 남는다.

양성 세 건은 모두 `target=Y, allowed=N`과 exact quote로 회수했다.
20 calls, runtime 22.663초, prompt/completion 128,671/597 tokens였고
source/provider/generation은 N002와 동일하다.

다음 최소 후보는 schema를 더 넓히지 않는다. target 정의에 두 관계만
organizer item boundary로 명시한다: (1) 기관/시설은 **입찰자 자체의
정체성·보유자원**이어야 하며 과거 실적의 발주처·납품처는 제외,
(2) 중소기업/소기업/소상공인 같은 기업규모 제한은 v1 기관유형이
아니다. 동시에 final v1=1이 아닌 관측에는 evidence를 요구하지 않는
reducer/evidence 계약을 분리한다. 이 두 변경은 한 실험에 섞지 않는다.

산출물: `outputs/clean-exp-n003-v1-axis-fast-v1/fast20/`.

# N002 v1 explicit-state fast20 result

작성일: 2026-09-22

결론: **FAIL. holdout/dev200 중단.** 명시적 Y/N/U 계약으로 N001의
전건 불명 문제는 해소됐지만, v1이 아닌 실적·지역 제한을 v1로
판정한 FP 4건이 생겼다.

| fast20 v1 | TP | FP | FN | U | invalid | F1(U→0 진단) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| N001 | 0 | 0 | 3 | 20 | 20 | 0.000000 |
| N002 | **3** | **4** | **0** | **1** | **1** | **0.600000** |

- calls: 20, finish_reason stop 20, runtime 34.879초
- prompt/completion tokens: 126,911 / 720
- Y positive quote: TP/FP 7건은 모두 exact source span에서 검증
- invalid 1건: `PPS-DEV-32`가 법정 등록 조건을 Y로 냈고 quote가
  원문 byte substring과 달라 U로 강등됨
- frozen/legacy fallback, 다른 item 변경: 없음

FP는 모두 같은 실패 유형이다.

- PPS-DEV-062: 최근 5년·3억원 행사 **실적** 제한
- PPS-DEV-051: 대학병원 납품 **실적** 제한
- PPS-DEV-042: 여행업 법정 등록 + 충청남도 **지역** 제한
- PPS-DEV-039: 경기/서울 **지역** 제한

반면 positive 3건은 정확히 회수했다.

- PPS-DEV-049: 체육교육학 전공이 있는 대학만
- PPS-DEV-072: 특정 지역의 교육시설 보유
- PPS-DEV-058: 대학·공공기관·국공립연구기관만

v31 카드는 실적·지역·등록·제품·기술을 다른 카드가 다루는 0 조건으로
명시했지만, 모델이 최종 Y/N을 직접 고를 때 그 축 분리가 지켜지지
않았다. 따라서 다음 실험은 같은 문구를 더 강조하는 final-label prompt가
아니라, 먼저 `기관/조직/자체 인력·시설 축의 제한이 있는가`와
`그 제한 자체에 허용 근거가 있는가`를 typed observation으로 분리한다.
Python은 명시된 상태의 conjunction만 수행하며 키워드/ID override를
하지 않는다.

baseline fast20 v1 F1=1.0과 비교하면 N002를 그대로 owner로 쓸 때
item F1 손실은 0.4, Macro 손실은 `0.4/24 = 0.016667`이다. 승격할
수 없다. 산출물은
`outputs/clean-exp-n002-v1-explicit-state-fast-v1/fast20/`이다.

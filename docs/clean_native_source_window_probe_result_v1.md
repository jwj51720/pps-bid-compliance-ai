# Native source-window 0-call coverage result

작성일: 2026-09-22

결론: **exact window index는 완전하지만 18,000자 bounded view는
final 입력으로 부적합하다.** gold 근거 2개가 빠졌고, selected source pack
자체만 최대 12,717 tokens라 24개 카드/metadata를 함께 넣을 여유도 없다.
이는 품질 실험이나 새 기준선 점수가 아니다.

| dev200 | 전체 index | 18,000자 bounded view |
| --- | ---: | ---: |
| 원문 스캔 문서 | 374/374 | 374/374 |
| source windows | 8,000 | 3,641 선택 / 4,359 제외 |
| exact gold nonempty evidence | 54/54 | 52/54 (96.30%) |
| Gemma calls | 0 | 0 |

bounded view의 source pack만 exact tokenizer로 3,674–12,717 tokens였고
전체 합계는 2,099,431 tokens였다. 별도 감사에서 24카드+metadata/product
고정 입력이 짧은 사례에도 약 9,093 tokens였으므로, bounded pack을 그
프롬프트에 그대로 더하는 설계는 admission 해법이 아니다. fixed prefix는
공고별로 달라질 수 있으므로 두 측정값을 더해 전 공고의 정확한 호출 수라고
주장하지 않는다.

제외된 gold 근거는 `PPS-DEV-23/v9`의 **규격서** 1개와
`PPS-DEV-139/v23`의 **공고문** 1개다. 이는 특정 공고용 lexeme을
추가하라는 근거가 아니다. 모든 문서를 index한 것과 최종 모델에 필요한
관계 사실을 전달한 것은 다르다. 특히 absence 항목 e10/e11/e16/e18/e20은
gold 근거가 항상 공란이므로 54/54조차 그 항목들의 부재 검증을 입증하지
못한다. 문서 간 반례·적용 예외·날짜 관계도 이 근거 recall로 검증되지 않는다.

따라서 현재 selector는 diagnostic으로 고정하고 paid quality run에는
사용하지 않는다. 다음 native 구조는 owner별로 필요한 source 역할을
선언하고, 후보 0개와 미관측을 구분하며, 긴 첨부에서 누락된 관계를
회수하는 coverage gate를 가져야 한다. 최종 호출에 필요한 카드·메타·제품
사실을 함께 admission해야 하므로 source view 크기만 따로 최적화하지 않는다.

재현:

```bash
.venv/bin/python scripts/audit_native_source_windows.py --input data/raw/open/dev.jsonl.gz --labels data/raw/open/dev_labels.csv --tokenizer-dir /Users/a60157288/.cache/huggingface/hub/models--google--gemma-4-26B-A4B-it/snapshots/4d7ae4984b7db7de8f8457170b3f1a419ee76d52 --char-cap 18000 --output-dir outputs/clean-native-source-window-probe-v1/dev200
```

ignored `audit.json`은 input/label hash, ID별 선택 source span의 doc ID/type/
offset/hash, item·문서 유형별 coverage, 누락 ID를 기록한다. 원문 근거
내용은 결과 문서에 복사하지 않았다.

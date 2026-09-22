# V2 source view v2: bounded atomic windows

작성일: 2026-09-22

v1 no-call audit는 374/374 documents와 gold e2 7/7을 보존했지만,
200건 중 15건이 14,848-token budget에서 task 계약용 1,200-token
여유를 확보하지 못했다. 최악 19,584 tokens였다. 반복적인 `실적`,
`특수 기술` anchor 창을 제한 없이 merge하면서 긴 제안요청서 본문이
통째로 들어간 것이 관찰됐다.

v2는 동일한 organizer 자료를 전 문서 scan하되 source 조각을 최대
1,600자 이내의 atomic window로 제한한다. 각 문서 첫 800자를
보존하고 나머지는 label-blind 우선순위로 총 14,000자 한도에 담는다.
우선순위는 하나의 조각 안에 참가자격과 실적이 함께 있는지, 실적·
참가자격 anchor 수, 문서 순서와 원문 위치다. 이 순위는 label/ID를
읽지 않고 source text와 organizer v2 truth condition에서만 나온다.
선정한 조각은 다시 문서 순서로 출력하고 exact SourceSpan provenance를
보존한다.

v1 view는 재현을 위해 그대로 두고 v2를 별도 함수로 둔다. v2는
무호출 audit에서 200/200 reserve admission과 gold e2 7/7이 확인되기
전까지 paid prompt의 입력으로 승격하지 않는다. 현재 1,200-token
reserve는 실제 task가 아직 없는 보수적 용량 proxy이며, 최종 task를
구현한 뒤 exact rendered tokenizer admission을 다시 수행해야 한다.

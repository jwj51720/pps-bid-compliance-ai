# INC-111: Gemma case-RAG pilot — partial success

On eight pre-frozen structural dev notices, both arms completed 8/8.  The
direct full-notice Gemma control scored 0.12500 macro positive F1; the only
change, addition of top-three BGE-retrieved unlabeled case records, scored
0.16667 (+0.04167).

The RAG arm changed seven cells: five direct false positives became correct
zeros (`v15`, `v23`, `v22`, `v12`) and one direct v12 false negative became a
correct positive.  It also introduced two v13/v15 false positives on one
notice.  This is a coherent but too-small net improvement, so it does not
authorize a 20k corpus scale or a merge.  It authorizes one fresh 16-notice
paired confirmation with the identical retrieval and prompt policy.

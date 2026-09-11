"""Offline historical diagnostic; never creates or selects submission labels.

Run from the repository root with .venv/bin/python scripts/analyze_astra_research_history.py.
All scores are independently reconstructed from archived CSVs, aligned by exact ID.
Bootstrap intervals describe notice resampling, not provider or public uncertainty.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data import competition_product_fact, load_competition_product_index
OUT = ROOT / "outputs/astra_research_audit_20260911"
ITEMS = [f"v{i}" for i in range(1, 25)]
ABSENCE = {9, 10, 15, 17, 19}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len({r["id"] for r in rows}) == len(rows), path
    return {r["id"]: r for r in rows}


def counts(y, p):
    tp = ((y == 1) & (p == 1)).sum(axis=0)
    fp = ((y == 0) & (p == 1)).sum(axis=0)
    fn = ((y == 1) & (p == 0)).sum(axis=0)
    den = 2 * tp + fp + fn
    f1 = np.divide(2 * tp, den, out=np.zeros(24), where=den > 0)
    return tp, fp, fn, f1


def describe(y, p):
    tp, fp, fn, f1 = counts(y, p)
    return {"n": len(y), "macro_f1": float(f1.mean()),
            "tp": int(tp.sum()), "fp": int(fp.sum()), "fn": int(fn.sum()),
            "per_item": [{"item": v, "tp": int(tp[i]), "fp": int(fp[i]),
                          "fn": int(fn[i]), "f1": float(f1[i])} for i, v in enumerate(ITEMS)]}


def matrix(rows, ids):
    return np.array([[int(rows[r][v]) for v in ITEMS] for r in ids])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    label_path = ROOT / "data/raw/open/dev_labels.csv"
    gold = read_csv(label_path)
    ids = list(gold)
    y = matrix(gold, ids)
    with gzip.open(ROOT / "data/raw/open/dev.jsonl.gz", "rt") as f:
        records = {r["id"]: r for r in map(json.loads, f)}
    assert set(records) == set(ids)
    history = []
    skipped = []
    for path in sorted((ROOT / "outputs").glob("*/metrics.json")):
        if "mock" in path.parent.name.lower():
            continue
        submission = path.parent / "submission.csv"
        if not submission.exists():
            skipped.append({"path": str(path.relative_to(ROOT)), "reason": "no submission"})
            continue
        try:
            rows = read_csv(submission)
            if not rows or not set(rows) <= set(gold):
                skipped.append({"path": str(path.relative_to(ROOT)), "reason": "non-dev IDs or empty"})
                continue
            score = describe(matrix(gold, list(rows)), matrix(rows, list(rows)))
            saved = json.loads(path.read_text())
            meta_path = path.parent / "run_meta.json"
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            history.append({"run": path.parent.name, "n": len(rows),
                            "macro_f1": score["macro_f1"], "tp": score["tp"],
                            "fp": score["fp"], "fn": score["fn"],
                            "recorded_f1": saved.get("leaderboard_metric", {}).get("macro_f1"),
                            "model": meta.get("model"), "runtime_seconds": meta.get("runtime_seconds"),
                            "cohort_sha256": hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest(),
                            "submission_sha256": hashlib.sha256(submission.read_bytes()).hexdigest()})
        except (KeyError, ValueError, AssertionError) as e:
            skipped.append({"path": str(path.relative_to(ROOT)), "reason": str(e)})
    report = {"label_sha256": hashlib.sha256(label_path.read_bytes()).hexdigest(),
              "history": history, "skipped": skipped, "runs": {}, "comparisons": {}}
    evidence = np.array([[bool(gold[r][f'e{i}']) for i in range(1, 25)] for r in ids])
    report["data"] = {"n": len(ids), "positive_cells": int(y.sum()),
                      "positive_with_evidence": int((y * evidence).sum()),
                      "positive_without_evidence": int((y * ~evidence).sum()),
                      "absence_positive": int(y[:, sorted(ABSENCE)].sum()),
                      "per_item_support": dict(zip(ITEMS, y.sum(axis=0).tolist())),
                      "blocks_25": [{"start_position": start + 1,
                                     "positive_cells": int(y[start:start+25].sum()),
                                     "notices_with_positive": int((y[start:start+25].sum(axis=1)>0).sum())}
                                    for start in range(0, 200, 25)]}
    products = load_competition_product_index(ROOT / 'data/derived/competition_products_v1.json')
    report['applicability_diagnostic'] = {
        'note': 'Observed metadata and exact lookup states, not legal verdicts or label overrides.',
        'v6_v7_positive_metadata': {
            v: [{'id': r, 'law': records[r]['meta']['적용계약법'],
                 'contract': records[r]['meta']['계약방법'],
                 'award': records[r]['meta']['낙찰방법']}
                for r in ids if gold[r][v] == '1'] for v in ('v6', 'v7')},
        'product_positive_lookup_states': {
            v: dict(Counter(competition_product_fact(records[r], products)['status']
                            for r in ids if gold[r][v] == '1')) for v in ITEMS[9:18]},
    }
    report['applicability_diagnostic']['conditional_product_entries'] = sum(
        bool(p.get('특이사항')) for p in products.values())
    report['applicability_diagnostic']['product_entry_count'] = len(products)
    report['applicability_diagnostic']['notices_matching_conditional_products'] = [
        {'id': r, 'estimated_price': records[r]['meta'].get('입찰추정가격'),
         'matched_notes': {code: products[code]['특이사항']
                           for code in competition_product_fact(records[r], products)['matched_codes']
                           if products[code].get('특이사항')}}
        for r in ids if any(products[c].get('특이사항')
                            for c in competition_product_fact(records[r], products)['matched_codes'])]
    matrices = {}
    for number in (120, 171, 172, 179, 190, 191):
        candidates = [h for h in history if h["run"].startswith(f"exp-{number}-")]
        assert len(candidates) == 1, (number, candidates)
        directory = ROOT / "outputs" / candidates[0]["run"]
        rows = read_csv(directory / "submission.csv")
        selected = [r for r in ids if r in rows]
        yy, pp = matrix(gold, selected), matrix(rows, selected)
        raw = [json.loads(l) for l in (directory / "predictions.jsonl").open()]
        raw_by_id = {r['id']: r for r in raw}
        assert set(raw_by_id) == set(selected)
        rr = [raw_by_id[r] for r in selected]
        run = describe(yy, pp)
        run["path"] = str(directory.relative_to(ROOT))
        run["pack_distribution"] = dict(Counter(len(r.get('pass_judgments', [])) for r in rr))
        run["final_calls_saved"] = sum(len(r.get('pass_judgments', [])) for r in rr)
        run["inventory_calls_saved"] = sum(len(r.get('staged_run', {}).get('inventory', {}).get('raw_responses', [])) for r in rr)
        run["parse_errors"] = sum(len(r.get('parse_errors', [])) for r in rr)
        run["record_aggregated_completion_over_2500"] = sum(r.get('usage', {}).get('completion_tokens', 0) > 2500 for r in rr)
        run["zero_tp_items"] = [x["item"] for x in run["per_item"] if x["tp"] == 0]
        run["perfect_precision_only_ceiling"] = float(counts(yy, pp * yy)[3].mean())
        ee = np.array([[bool(gold[r][f'e{i}']) for i in range(1, 25)] for r in selected])
        run["positive_recall_by_gold_evidence"] = {
            str(flag): {"support": int((yy * (ee == flag)).sum()),
                        "tp": int((yy * pp * (ee == flag)).sum())} for flag in (True, False)}
        if all(r.get('pass_judgments') for r in rr):
            before = np.array([[int(all(p[v]['위반여부'] for p in r['pass_judgments']))
                                if i in ABSENCE else int(any(p[v]['위반여부'] for p in r['pass_judgments']))
                                for i, v in enumerate(ITEMS)] for r in rr])
            run["before_frozen_rules"] = describe(yy, before)
            run["post_pass_changed_cells"] = int((before != pp).sum())
        if len(selected) == 200:
            run["slices"] = {}
            for label, mask in {
                "first75": np.arange(200) < 75, "remaining125": np.arange(200) >= 75,
                "single_pack": np.array([len(r.get('pass_judgments', [])) == 1 for r in rr]),
                "multi_pack": np.array([len(r.get('pass_judgments', [])) > 1 for r in rr]),
            }.items():
                run["slices"][label] = describe(yy[mask], pp[mask])
        report['runs'][str(number)] = run
        matrices[number] = (selected, yy, pp, raw_by_id)
    a, b = matrices[171][2], matrices[172][2]
    rng = np.random.default_rng(20260911)
    differences = []
    for _ in range(5000):
        sample = rng.integers(0, 200, 200)
        differences.append(float(counts(y[sample], a[sample])[3].mean() - counts(y[sample], b[sample])[3].mean()))
    report['comparisons']['171_minus_172'] = {
        'paired_notice_bootstrap_5000_percentile95': np.quantile(differences, [.025, .975]).tolist(),
        'changed_cells': int((a != b).sum()),
        'became_correct': int(((a == y) & (b != y)).sum()),
        'became_wrong': int(((a != y) & (b == y)).sum()),
        'per_item_macro_contribution': dict(zip(ITEMS, ((counts(y,a)[3]-counts(y,b)[3])/24).tolist()))}
    for number in (190, 191):
        selected, yy, pp, raw = matrices[number]
        normal = np.array([[raw[r]['staged_run']['normal_final']['judgment'][v]['위반여부']
                            for v in ITEMS] for r in selected])
        base_ids, _, base_p, _ = matrices[179]
        assert selected == base_ids
        report['comparisons'][f'{number}_specialist'] = {
            'same_run_normal_final': describe(yy, normal), 'specialist_final': describe(yy, pp),
            'normal_vs179_changed_cells': int((normal != base_p).sum()),
            'non_v23_vs179_changed_cells': int((np.delete(normal,22,axis=1) != np.delete(base_p,22,axis=1)).sum()),
            'normal_vs179_macro_delta': float(counts(yy,normal)[3].mean()-counts(yy,base_p)[3].mean()),
            'specialist_same_run_macro_delta': float(counts(yy,pp)[3].mean()-counts(yy,normal)[3].mean())}
    report['documents'] = [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                            "lines": len(p.read_text().splitlines())}
                           for folder in ('docs', 'incubator/docs') for p in sorted((ROOT/folder).rglob('*.md'))
                           if p.name != '20260911_astra_performance_diagnosis.md']
    (OUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Historical metric files reconstructed:', len(history), 'skipped:', len(skipped))
    print('Metric mismatches:', [h['run'] for h in history if h['recorded_f1'] is not None and abs(h['macro_f1']-h['recorded_f1'])>1e-9])
    for k, r in report['runs'].items():
        print(k, {x:r[x] for x in ('n','macro_f1','tp','fp','fn','zero_tp_items','perfect_precision_only_ceiling','post_pass_changed_cells') if x in r})
    for name, comparison in report['comparisons'].items():
        print(name, {k:v for k,v in comparison.items()
                     if k not in ('same_run_normal_final', 'specialist_final', 'per_item_macro_contribution')})
    print('Artifact:', OUT / 'audit.json')


if __name__ == '__main__':
    main()

# Dev fast panel v1

`configs/dev_fast_panel_v1.json` is the default local fast-evaluation cohort.
It replaces file-order `first-20` for new fast experiments. The list is ordered,
versioned, and included in the run selection signature.

## Contract

- It contains 20 dev notices, all 24 positive-class labels at least once, 38
  positive labels total, and an 8 national / 12 local contract-law split.
- It has five notices in each dev-200 total-document-length quartile.
- Its selection used only dev labels and stable input properties, never prior
  model predictions or scores. The ID list is frozen at v1.
- It is a fast ranking gate, not a performance estimate or a substitute for a
  dev-200 run. Its positive rate is intentionally enriched, so it must not
  select a canonical submission policy by itself.

## Historical alignment check

The panel was selected before reading historical prediction outputs. Applied
afterwards to the four completed dev-200 prediction files, its mean absolute
Macro-F1 error versus dev-200 was 0.0142, compared with 0.0739 for file-order
first-20. The four experiments are too few to treat that as a calibrated
leaderboard estimator; it only supports using this panel as a better fast gate.

| Experiment | File-order first-20 | Fast panel v1 | Dev-200 |
|---|---:|---:|---:|
| EXP001 | 0.0903 | 0.1736 | 0.2204 |
| EXP004 | 0.1284 | 0.2110 | 0.2138 |
| EXP013 | 0.1175 | 0.1762 | 0.1742 |
| EXP014 | 0.2046 | 0.2333 | 0.2280 |

## Use

For a config with `data.fast_panel_ids_path: configs/dev_fast_panel_v1.json`,
`python scripts/run_experiment.py --config <config>` selects this exact panel.
The grouped runner follows the same config field. A dev-200 config must set the
field to `null` and use `run.local_limit: null` (or explicitly pass `--limit 200`).
`--ids-file` remains an explicit override for one-off selections.

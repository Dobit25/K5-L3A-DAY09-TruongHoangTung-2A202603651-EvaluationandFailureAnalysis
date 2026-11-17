import copy

from lab9.gate import integrity_check


ROWS = [
    {"item_id": f"E-{i:03d}", "seed": seed, "pass_rate": True, "slices": ["money_movement"]}
    for i in range(2) for seed in (11, 22)
]
SPEC = {
    "eval_set_version": "v2",
    "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True,
         "threshold": {"min": 0.8, "no_significant_drop": True}},
    ],
    "slices": [
        {"name": "money_movement", "metric": "pass_rate", "min": 0.8,
         "no_significant_drop": True, "blocking": True},
    ],
}


def _report(rows=None):
    return {
        "manifest": {"items": 2, "seeds": [11, 22], "eval_set_sha": "x"},
        "rows": copy.deepcopy(ROWS if rows is None else rows),
        "metrics": {"pass_rate": 1.0},
        "evaluator_failures": [],
    }


def test_integrity_rejects_duplicate_rows_and_slice_relabelling():
    base = _report()
    duplicate = _report([*ROWS[:-1], ROWS[0]])
    assert any("duplicate" in p for p in integrity_check(duplicate, base, SPEC))

    relabelled = _report()
    relabelled["rows"][0]["slices"] = []
    assert any("slice tags" in p for p in integrity_check(relabelled, base, SPEC))


def test_integrity_rejects_evaluator_failure_and_missing_value():
    base = _report()
    broken = _report()
    broken["evaluator_failures"] = ["grader crashed"]
    broken["rows"][0]["pass_rate"] = None
    problems = integrity_check(broken, base, SPEC)
    assert any("evaluator_failures" in p for p in problems)
    assert any("missing" in p for p in problems)


def test_ratchet_rejects_removed_or_weakened_metric_and_slice():
    base = _report()
    weakened = copy.deepcopy(SPEC)
    weakened["metrics"][0]["blocking"] = False
    weakened["metrics"][0]["threshold"] = {"min": 0.5}
    weakened["slices"] = []
    problems = integrity_check(base, base, weakened, SPEC)
    assert any("non-blocking" in p for p in problems)
    assert any("minimum" in p for p in problems)
    assert any("no_significant_drop" in p for p in problems)
    assert any("slice" in p and "disappeared" in p for p in problems)

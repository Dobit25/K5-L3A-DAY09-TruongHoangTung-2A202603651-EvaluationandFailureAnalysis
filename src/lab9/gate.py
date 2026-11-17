"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []

    for metric, value in (pr.get("metrics") or {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isfinite(value):
            problems.append(f"metric {metric} is not finite")
    for metric in spec.get("metrics") or []:
        if metric["id"] not in (pr.get("metrics") or {}):
            problems.append(f"aggregate metric {metric['id']} is missing")

    rows = pr.get("rows") or []
    manifest = pr.get("manifest") or {}
    expected_count = int(manifest.get("items") or 0) * len(manifest.get("seeds") or [])
    if len(rows) != expected_count:
        problems.append(f"row count {len(rows)} != manifest {expected_count}")

    def pairs(report: dict) -> list[tuple[object, object]]:
        return [(r.get("item_id"), r.get("seed")) for r in report.get("rows") or []]

    pr_pairs = pairs(pr)
    base_pairs = pairs(base)
    if len(set(pr_pairs)) != len(pr_pairs):
        problems.append("duplicate (item_id, seed) rows")
    if set(pr_pairs) != set(base_pairs):
        problems.append("PR item/seed set differs from baseline")

    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures is non-empty")
    graded = [m["id"] for m in spec.get("metrics") or [] if m["id"] in GRADERS]
    for row in rows:
        for metric in graded:
            if row.get(metric) is None:
                problems.append(f"{row.get('item_id')}@{row.get('seed')}: {metric} is missing")

    base_slices = {(r.get("item_id"), r.get("seed")): tuple(sorted(r.get("slices") or []))
                   for r in base.get("rows") or []}
    for row in rows:
        key = (row.get("item_id"), row.get("seed"))
        if key in base_slices and tuple(sorted(row.get("slices") or [])) != base_slices[key]:
            problems.append(f"{key[0]}@{key[1]}: slice tags differ from baseline")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems.extend(_ratchet_problems(spec, base_spec))
    return sorted(set(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices") or []:
        name, metric = entry["name"], entry["metric"]
        pr_values = per_item(pr, metric, slice_name=name)
        base_values = per_item(base, metric, slice_name=name)
        value = sum(pr_values.values()) / len(pr_values) if pr_values else None
        verdict, note = "ok", ""
        if value is None:
            verdict = "missing"
        elif "min" in entry and value < float(entry["min"]):
            verdict = "fail"
        elif "max" in entry and value > float(entry["max"]):
            verdict = "fail"
        if entry.get("no_significant_drop") and value is not None:
            keys = sorted(set(pr_values) & set(base_values))
            if not keys:
                verdict = "missing"
                note = "no paired items"
            else:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_values[k] for k in keys], [base_values[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        metric_id = f"slice:{name}/{metric}"
        if verdict != "ok" and entry.get("blocking"):
            blocked.append(metric_id)
        label = "ok" if verdict == "ok" else ("BLOCK" if entry.get("blocking") else "warn")
        lines.append(f"  {metric_id:<32} {value!s:<8} {note:<28} {label}")
    return blocked, lines


def _ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    """Same eval-set version permits equal or stricter gates, never looser ones."""
    problems: list[str] = []

    def indexed(entries: list[dict], *, slices: bool = False) -> dict:
        if slices:
            return {(e.get("name"), e.get("metric")): e for e in entries}
        return {e.get("id"): e for e in entries}

    def compare(current: dict, previous: dict, label: str) -> None:
        if previous.get("blocking") and not current.get("blocking"):
            problems.append(f"ratchet: {label} changed from blocking to non-blocking")
        old, new = previous.get("threshold", previous), current.get("threshold", current)
        if "min" in old and ("min" not in new or float(new["min"]) < float(old["min"])):
            problems.append(f"ratchet: {label} minimum was loosened")
        if "max" in old and ("max" not in new or float(new["max"]) > float(old["max"])):
            problems.append(f"ratchet: {label} maximum was loosened")
        if "max_increase" in old and ("max_increase" not in new or
                                       float(new["max_increase"]) > float(old["max_increase"])):
            problems.append(f"ratchet: {label} max_increase was loosened")
        if old.get("no_significant_drop") and not new.get("no_significant_drop"):
            problems.append(f"ratchet: {label} dropped no_significant_drop")

    for key, previous in indexed(base_spec.get("metrics") or []).items():
        current = indexed(spec.get("metrics") or []).get(key)
        if current is None:
            problems.append(f"ratchet: metric {key} disappeared")
        else:
            compare(current, previous, f"metric {key}")
    current_slices = indexed(spec.get("slices") or [], slices=True)
    for key, previous in indexed(base_spec.get("slices") or [], slices=True).items():
        current = current_slices.get(key)
        if current is None:
            problems.append(f"ratchet: slice {key[0]}/{key[1]} disappeared")
        else:
            compare(current, previous, f"slice {key[0]}/{key[1]}")
    return problems


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
NLVL pilot - step 3: score the predictions.

Metrics
  tIoU            overlap of the predicted interval with the true interval
  R@0.3, R@0.5    fraction of positive queries whose tIoU clears that value
  rejection acc.  fraction of negative queries the system correctly refused
Only E3 can refuse, so rejection accuracy is 0 by construction for E1 and E2.
"""
import argparse, json, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root


def tiou(pred, gt):
    if pred[0] is None:
        return 0.0
    ps, pe = pred
    gs, ge = gt
    # intervals are inclusive of both endpoint seconds, hence the +1
    inter = max(0.0, min(pe, ge) - max(ps, gs) + 1.0)
    union = (pe - ps + 1.0) + (ge - gs + 1.0) - inter
    return inter / union if union > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()

    out = f"{a.root}/outputs/{a.model}"
    P = json.load(open(f"{out}/predictions.json"))
    qs = json.load(open(f"{a.root}/data/queries.json"))["queries"]
    GT = json.load(open(f"{a.root}/data/ground_truth.json"))["intervals"]
    byid = {q["id"]: q for q in qs}
    pos = [q["id"] for q in qs if q["type"] == "positive"]
    neg = [q["id"] for q in qs if q["type"] != "positive"]
    hard = [q["id"] for q in qs if q["type"] == "hard_negative"]
    easy = [q["id"] for q in qs if q["type"] == "easy_negative"]

    summary, per_query = {}, {}
    for variant, rows in P["predictions"].items():
        ious = {}
        for i in pos:
            g = (GT[i]["start"], GT[i]["end"])
            ious[i] = tiou((rows[i]["start"], rows[i]["end"]), g)
        v = np.array([ious[i] for i in pos])
        rej = {k: (not rows[k].get("accepted", True)) for k in neg}
        summary[variant] = {
            "mean_tIoU": float(v.mean()), "median_tIoU": float(np.median(v)),
            "R@0.3": float((v >= 0.3).mean()), "R@0.5": float((v >= 0.5).mean()),
            "rejection_acc_all_neg": float(np.mean([rej[k] for k in neg])),
            "rejection_acc_hard": float(np.mean([rej[k] for k in hard])),
            "rejection_acc_easy": float(np.mean([rej[k] for k in easy])),
            "false_abstain_on_positives": int(sum(
                1 for i in pos if not rows[i].get("accepted", True))),
        }
        per_query[variant] = {
            i: {"name": byid[i]["name"], "type": byid[i]["type"],
                "pred": [rows[i]["start"], rows[i]["end"]],
                "gt": [GT[i]["start"], GT[i]["end"]] if i in GT else None,
                "tIoU": round(ious[i], 4) if i in ious else None,
                "peak_t": rows[i]["peak_t"], "abs_score": round(rows[i]["abs_score"], 4),
                "margin": round(rows[i]["margin"], 4),
                "peakiness": round(rows[i]["peakiness"], 3),
                "accepted": rows[i].get("accepted", True)}
            for i in byid}

    res = {"model": a.model, "thresholds": P["thresholds"],
           "summary": summary, "per_query": per_query}
    json.dump(res, open(f"{out}/results.json", "w"), indent=2)

    hdr = f"{'variant':<15}{'mean tIoU':>10}{'med tIoU':>10}{'R@0.3':>8}{'R@0.5':>8}{'rej all':>9}{'rej hard':>10}{'rej easy':>10}"
    print(f"\n=== {a.model} ===\n{hdr}\n{'-'*len(hdr)}")
    for k, s in summary.items():
        print(f"{k:<15}{s['mean_tIoU']:>10.3f}{s['median_tIoU']:>10.3f}"
              f"{s['R@0.3']:>8.2f}{s['R@0.5']:>8.2f}"
              f"{s['rejection_acc_all_neg']:>9.2f}{s['rejection_acc_hard']:>10.2f}"
              f"{s['rejection_acc_easy']:>10.2f}")

    print(f"\nper-query (E2_temporal):")
    print(f"{'id':<4}{'name':<18}{'type':<15}{'gt':>12}{'pred':>14}{'tIoU':>7}{'abs':>8}{'peaky':>7}")
    for i, r in per_query["E2_temporal"].items():
        g = f"[{r['gt'][0]},{r['gt'][1]}]" if r["gt"] else "-"
        p = f"[{r['pred'][0]:.0f},{r['pred'][1]:.0f}]" if r["pred"][0] is not None else "REJECT"
        iou = "-" if r["tIoU"] is None else f"{r['tIoU']:.3f}"
        print(f"{i:<4}{r['name']:<18}{r['type']:<15}{g:>12}{p:>14}{iou:>7}"
              f"{r['abs_score']:>8.3f}{r['peakiness']:>7.2f}")
    print(f"\nwrote {out}/results.json")


if __name__ == "__main__":
    main()

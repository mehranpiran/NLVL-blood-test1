#!/usr/bin/env python3
"""
NLVL pilot - step 2: turn embeddings into predicted time intervals.

Three cumulative variants are produced:
  E1 baseline   : every frame scored independently, interval from the raw curve
  E2 temporal   : the same, after smoothing the score curve over time
  E3 abstention : E2, but the system may refuse to answer

Thresholds for E3 are fitted on the EASY NEGATIVES ONLY, never on the positives
or on the hard negatives, so the hard negatives stay an honest test.
"""
import argparse, json, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root


def smooth(s, w=(0.25, 0.5, 0.25)):
    """Weighted 3-tap average along time, with edges handled by renormalising."""
    n = len(s)
    out = np.empty(n, dtype=np.float64)
    for t in range(n):
        acc = wsum = 0.0
        for k, wk in zip((-1, 0, 1), w):
            u = t + k
            if 0 <= u < n:
                acc += wk * s[u]
                wsum += wk
        out[t] = acc / wsum
    return out


def interval_from_curve(s, times, beta=0.70):
    """
    Grow a single contiguous interval outwards from the peak frame, keeping
    frames whose score is within the top (1-beta) of the curve's own range.
    beta=0.70 means: keep frames scoring at least 70% of the way from the
    minimum to the maximum of this query's curve.
    """
    lo, hi = float(s.min()), float(s.max())
    if hi - lo < 1e-9:                       # perfectly flat curve
        return float(times[0]), float(times[-1]), int(np.argmax(s))
    thr = lo + beta * (hi - lo)
    p = int(np.argmax(s))
    i = p
    while i - 1 >= 0 and s[i - 1] >= thr:
        i -= 1
    j = p
    while j + 1 < len(s) and s[j + 1] >= thr:
        j += 1
    return float(times[i]), float(times[j]), p


def confidences(S, peaks):
    """
    For each query q with peak frame t*:
      abs_score : the cosine similarity at the peak
      margin    : how far q beats the best competing query at that same frame
      peakiness : how far the peak stands out above q's own curve, in sigmas
    """
    nq = S.shape[0]
    out = []
    for q in range(nq):
        t = peaks[q]
        col = S[:, t].copy()
        mine = col[q]
        col[q] = -np.inf
        out.append({
            "abs_score": float(mine),
            "margin": float(mine - col.max()),
            "peakiness": float((S[q].max() - np.median(S[q])) / (S[q].std() + 1e-9)),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--beta", type=float, default=0.70)
    a = ap.parse_args()

    out = f"{a.root}/outputs/{a.model}"
    z = np.load(f"{out}/embeddings.npz", allow_pickle=True)
    F, T, times = z["frame_emb"], z["text_emb"], z["times"]
    qs = json.load(open(f"{a.root}/data/queries.json"))["queries"]
    qid = [q["id"] for q in qs]
    assert list(z["query_ids"]) == qid, "query order changed since encoding"

    S_raw = T @ F.T                                   # cosine, (n_query, n_frame)
    S_sm = np.stack([smooth(S_raw[q]) for q in range(len(qid))])

    preds = {}
    for name, S in (("E1_baseline", S_raw), ("E2_temporal", S_sm)):
        rows = {}
        peaks = []
        for q, qq in enumerate(qs):
            s, e, p = interval_from_curve(S[q], times, a.beta)
            peaks.append(p)
            rows[qq["id"]] = {"start": s, "end": e, "peak_t": float(times[p])}
        for q, qq in enumerate(qs):
            rows[qq["id"]].update(confidences(S, peaks)[q])
        preds[name] = rows

    # ---- E3: abstention, thresholds fitted on the easy negatives only ----
    easy = [q["id"] for q in qs if q["type"] == "easy_negative"]
    base = preds["E2_temporal"]
    tau_abs = max(base[i]["abs_score"] for i in easy)
    tau_mar = max(base[i]["margin"] for i in easy)
    rows = {}
    for qq in qs:
        r = dict(base[qq["id"]])
        accept = (r["abs_score"] > tau_abs) and (r["margin"] > tau_mar)
        r["accepted"] = bool(accept)
        if not accept:
            r["start"] = r["end"] = None
        rows[qq["id"]] = r
    preds["E3_abstention"] = rows

    res = {"model": a.model, "beta": a.beta,
           "thresholds": {"tau_absolute": tau_abs, "tau_margin": tau_mar,
                          "fitted_on": easy},
           "predictions": preds}
    with open(f"{out}/predictions.json", "w") as fh:
        json.dump(res, fh, indent=2)
    np.savez_compressed(f"{out}/scores.npz", S_raw=S_raw, S_smooth=S_sm, times=times,
                        query_ids=np.array(qid))
    print(f"[{a.model}] tau_absolute={tau_abs:.4f}  tau_margin={tau_mar:.4f}  "
          f"(fitted on {', '.join(easy)})")
    print(f"[{a.model}] wrote {out}/predictions.json and scores.npz")


if __name__ == "__main__":
    main()

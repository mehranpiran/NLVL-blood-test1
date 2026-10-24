#!/usr/bin/env python3
"""
NLVL pilot - the time-reversal experiment.

Playing a venipuncture clip backwards turns every action into its opposite while
leaving the pixels untouched. That gives a perfectly controlled test of whether a
model understands the direction of an action.

Part 1  shows that the existing pipeline CANNOT pass this test, by construction.
        Under reversal the multiset of per-frame scores is unchanged, so any
        order-invariant pooling gives an identical number, and a symmetric
        smoothing kernel merely mirrors the curve. This is verified numerically
        rather than merely asserted.

Part 2  asks whether an asymmetric operator can pass it. The displacement
        d = f(last) - f(first) flips sign under reversal, so a classifier through
        the origin is exactly antisymmetric and cannot cheat. Evaluation is
        leave-one-SHOOT-out, because clips from one shoot share a room, a patient
        and a camera.
"""
import argparse, json, os
from math import comb
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root


def binom_p(k, n, p=0.5):
    """Two-sided exact binomial test."""
    probs = [comb(n, i) * p**i * (1-p)**(n-i) for i in range(n+1)]
    obs = probs[k]
    return min(1.0, sum(q for q in probs if q <= obs * (1 + 1e-9)))


def smooth(s, w=(0.25, 0.5, 0.25)):
    n = len(s); out = np.empty(n)
    for t in range(n):
        acc = ws = 0.0
        for k, wk in zip((-1, 0, 1), w):
            u = t + k
            if 0 <= u < n:
                acc += wk * s[u]; ws += wk
        out[t] = acc / ws
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip_l14")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()

    emb = f"{a.root}/corpus/emb/{a.model}"
    Z = np.load(f"{emb}/corpus_frames.npz")
    IDX = json.load(open(f"{emb}/corpus_index.json"))
    names = [r["name"] for r in IDX]
    shoots = {r["name"]: r["shoot"] for r in IDX}

    # a caption only used to demonstrate the invariance in Part 1
    tq = np.load(f"{a.root}/outputs/{a.model}/embeddings.npz", allow_pickle=True)
    qids = list(tq["query_ids"]); T = tq["text_emb"]
    t_insert = T[qids.index("p3")]

    # ---------------- Part 1: the pipeline cannot tell forward from reversed ---
    print("=" * 74)
    print("PART 1  Is the existing pipeline sensitive to time reversal?")
    print("=" * 74)
    print(f"{'clip':<42}{'max fwd':>9}{'max rev':>9}{'|diff|':>10}")
    worst = 0.0
    for n in names:
        F = Z[n]
        s_f = smooth(F @ t_insert)
        s_r = smooth(F[::-1] @ t_insert)
        mf, mr = s_f.max(), s_r.max()
        worst = max(worst, abs(mf - mr))
        if n in names[:4]:
            print(f"{n[:40]:<42}{mf:>9.5f}{mr:>9.5f}{abs(mf-mr):>10.2e}")
    print(f"{'...':<42}")
    print(f"\nlargest difference over all {len(names)} clips: {worst:.3e}")
    print("The score is identical to numerical precision. A symmetric filter over")
    print("per-frame scores is time-reversal equivariant, so this pipeline is at")
    print("exactly 50% on the direction task BY CONSTRUCTION, not by bad luck.")

    # ---------------- Part 2: an asymmetric operator ---------------------------
    print()
    print("=" * 74)
    print("PART 2  Can the displacement in embedding space tell them apart?")
    print("=" * 74)
    D, S = [], []
    for n in names:
        F = Z[n]
        d = F[-1] - F[0]                      # flips sign exactly under reversal
        nd = np.linalg.norm(d)
        if nd < 1e-9:
            print(f"  skip {n}: zero displacement"); continue
        D.append(d / nd); S.append(shoots[n])
    D = np.array(D); S = np.array(S)
    uniq = sorted(set(S))
    print(f"{len(D)} clips, {len(uniq)} shoots: {uniq}")

    # leave-one-shoot-out, centroid direction, classifier through the origin
    correct, per_shoot = [], {}
    for sh in uniq:
        te = S == sh; tr = ~te
        if tr.sum() < 2: continue
        w = D[tr].mean(0)                     # learned "direction of progress"
        nw = np.linalg.norm(w)
        if nw < 1e-12:
            pred = np.zeros(te.sum()); 
        else:
            pred = D[te] @ (w / nw)
        ok = (pred > 0).astype(int)           # forward clips should score positive
        per_shoot[sh] = (int(ok.sum()), int(te.sum()), float(pred.mean()))
        correct.extend(ok.tolist())
    k, n = int(sum(correct)), len(correct)
    print(f"\n{'held-out shoot':<18}{'correct':>9}{'n':>5}{'mean margin':>14}")
    for sh in uniq:
        if sh in per_shoot:
            c, t, m = per_shoot[sh]
            print(f"{sh:<18}{c:>9}{t:>5}{m:>14.4f}")
    print(f"\nleave-one-shoot-out accuracy: {k}/{n} = {k/n:.3f}   "
          f"(chance 0.500, exact binomial p = {binom_p(k, n):.4f})")
    print("Because reversing a clip negates d exactly, a reversed clip is classified")
    print("correctly whenever its forward version is: the 2N decisions carry N bits,")
    print(f"so N = {n} is the honest sample size.")

    json.dump({"model": a.model, "invariance_max_diff": float(worst),
               "loso_correct": k, "loso_n": n, "loso_acc": k/n,
               "binomial_p": binom_p(k, n),
               "per_shoot": {s: per_shoot[s] for s in per_shoot}},
              open(f"{emb}/arrow_of_time.json", "w"), indent=1)
    print(f"\nwrote {emb}/arrow_of_time.json")


if __name__ == "__main__":
    main()

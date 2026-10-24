#!/usr/bin/env python3
"""
Figures for the multi-video / time-reversal study.

Scripts 07-09 printed their numbers and saved JSON but drew nothing. This draws
the four results the abstract states. It recomputes rather than trusting the
JSON wherever the per-item values were not saved.

  fig_mv1_corpus.png        what the corpus is: 21 clips, 11 shoots, 460 frames
  fig_mv2_reversal.png      forward vs reversed score, per clip, log scale
  fig_mv3_null_tests.png    the four order-sensitive tests against chance
  fig_mv4_orthogonality.png why they fail: steps are perpendicular to language
"""
import argparse, glob, json, os
from math import comb
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
ap = argparse.ArgumentParser()
ap.add_argument("--root", default=ROOT)
ap.add_argument("--model", default="clip_l14")
ap.add_argument("--outdir", required=True)
A = ap.parse_args()
os.makedirs(A.outdir, exist_ok=True)

EMB = f"{A.root}/corpus/emb/{A.model}"
Z = np.load(f"{EMB}/corpus_frames.npz")
IDX = json.load(open(f"{EMB}/corpus_index.json"))
ARROW = json.load(open(f"{EMB}/arrow_of_time.json"))
CAPD = json.load(open(f"{EMB}/caption_direction.json"))
FPSJ = json.load(open(f"{EMB}/fps_check_frames_4fps.json"))

C_OK, C_BAD, C_DARK, C_GREY = "#2a9d8f", "#c1121f", "#264653", "#9aa5ab"


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


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return max(0, c-h), min(1, c+h)


def binom_p(k, n, p=0.5):
    pr = [comb(n, i) * p**i * (1-p)**(n-i) for i in range(n+1)]
    return min(1.0, sum(q for q in pr if q <= pr[k] * (1 + 1e-9)))


# ================= FIGURE 1: the corpus =================
rows = sorted(IDX, key=lambda r: (r["shoot"], r["name"]))
shoots = sorted({r["shoot"] for r in rows})
cmap = plt.get_cmap("tab20")
col = {s: cmap(i % 20) for i, s in enumerate(shoots)}
nfr = [len(Z[r["name"]]) for r in rows]
lab = [f'{r["shoot"]}  {r["name"][:34]}' for r in rows]

fig, ax = plt.subplots(figsize=(10, 6.2))
y = np.arange(len(rows))
ax.barh(y, nfr, color=[col[r["shoot"]] for r in rows], height=0.72)
for i, v in enumerate(nfr):
    ax.text(v + 0.5, i, str(v), va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=7.5)
ax.invert_yaxis()
ax.set_xlabel("frames sampled at one per second", fontsize=9.5)
ax.set_title(f"The corpus: {len(rows)} clips from {len(shoots)} independent shoots, "
             f"{sum(nfr)} frames in total", fontsize=11)
ax.tick_params(labelsize=8.5)
handles = [plt.Rectangle((0, 0), 1, 1, color=col[s]) for s in shoots]
ax.legend(handles, [f"shoot {s}" for s in shoots], fontsize=7.5, ncol=6,
          loc="upper center", bbox_to_anchor=(0.5, -0.08), framealpha=0.9)
ax.set_xlim(0, max(nfr) * 1.07)
fig.tight_layout()
fig.savefig(f"{A.outdir}/fig_mv1_corpus.png", dpi=170, bbox_inches="tight")
plt.close(fig)

# ================= FIGURE 2: reversal invariance =================
tq = np.load(f"{A.root}/outputs/{A.model}/embeddings.npz", allow_pickle=True)
qids = list(tq["query_ids"]); t_insert = tq["text_emb"][qids.index("p3")]
diffs, names2 = [], []
for r in rows:
    F = Z[r["name"]]
    d = abs(smooth(F @ t_insert).max() - smooth(F[::-1] @ t_insert).max())
    diffs.append(d); names2.append(f'{r["shoot"]}  {r["name"][:34]}')
diffs = np.array(diffs)
FLOOR = 1e-12
plotted = np.where(diffs > 0, diffs, FLOOR)

fig, ax = plt.subplots(figsize=(10, 6.2))
y = np.arange(len(rows))
is_zero = diffs == 0
ax.barh(y, plotted, color=[C_GREY if z else C_DARK for z in is_zero], height=0.72)
ax.set_xscale("log")
ax.axvline(np.finfo(np.float32).eps, color=C_BAD, lw=1.6, ls="--",
           label=f"float32 precision ({np.finfo(np.float32).eps:.1e})")
ax.axvline(0.01, color=C_OK, lw=1.6, ls=":",
           label="size of a real difference between two queries (about 0.01)")
ax.set_yticks(y); ax.set_yticklabels(names2, fontsize=7.5)
ax.invert_yaxis()
ax.set_xlim(1e-13, 1)
ax.set_xlabel("difference between the forward score and the reversed score (log scale)",
              fontsize=9.5)
ax.set_title("Playing every clip backwards changes the score by nothing at all\n"
             f"largest difference over all {len(rows)} clips: "
             f"{ARROW['invariance_max_diff']:.2e}", fontsize=11)
h, l = ax.get_legend_handles_labels()
h.append(plt.Rectangle((0, 0), 1, 1, color=C_GREY))
l.append(f"difference exactly zero ({int(is_zero.sum())} clips, drawn at the left edge)")
ax.legend(h, l, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.09),
          framealpha=0.95)
ax.tick_params(labelsize=8.5)
fig.tight_layout()
fig.savefig(f"{A.outdir}/fig_mv2_reversal.png", dpi=170, bbox_inches="tight")
plt.close(fig)

# ================= FIGURE 3: the null tests =================
tests = [("shared direction\nleave-one-shoot-out", ARROW["loso_correct"], ARROW["loso_n"]),
         ("caption direction\nzero-shot", CAPD["correct"], CAPD["n"])]
for stat, nice in (("endpoint", "endpoint shift\n4 fps"),
                   ("step_vote", "step vote\n4 fps"),
                   ("step_mean", "mean step\n4 fps")):
    k = sum(r[stat] > 0 for r in FPSJ)
    tests.append((nice, k, len(FPSJ)))

fig, ax = plt.subplots(figsize=(10, 4.0))
x = np.arange(len(tests))
acc = [k/n for _, k, n in tests]
lo = [a - wilson(k, n)[0] for a, (_, k, n) in zip(acc, tests)]
hi = [wilson(k, n)[1] - a for a, (_, k, n) in zip(acc, tests)]
bars = ax.bar(x, acc, 0.55, color=C_GREY, edgecolor=C_DARK, lw=1.1)
ax.errorbar(x, acc, yerr=[lo, hi], fmt="none", ecolor=C_DARK, capsize=4, lw=1.2)
ax.axhline(0.5, color=C_BAD, lw=1.6, ls="--", label="chance (50 per cent)")
for i, (nm, k, n) in enumerate(tests):
    ax.text(i, acc[i] + hi[i] + 0.05, f"{k}/{n}\np = {binom_p(k, n):.2f}",
            ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([t[0] for t in tests], fontsize=8.5)
ax.set_ylim(0, 1.32)
ax.set_ylabel("share of clips given the correct direction", fontsize=9.5)
ax.set_title("Every attempt to recover the direction of the action landed on chance",
             fontsize=11)
ax.legend(fontsize=8.5, loc="upper right", framealpha=0.95)
ax.tick_params(labelsize=8.5)
fig.tight_layout()
fig.savefig(f"{A.outdir}/fig_mv3_null_tests.png", dpi=170)
plt.close(fig)


print("WROTE figures 1-3 to", A.outdir)

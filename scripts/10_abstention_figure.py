#!/usr/bin/env python3
"""
Figure for the abstention claim in the abstract.

The existing fig4_summary.png pools all seven negatives into one rejection bar,
so it cannot show the claim "rejected all easy negatives and one of four hard
negatives without reducing localisation accuracy". This script draws that claim
directly: rejection split by negative type on the left, and the cost paid in
localisation accuracy on the right.
"""
import argparse, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=".")
ap.add_argument("--model", default="clip_l14")
ap.add_argument("--out", required=True)
A = ap.parse_args()

S = json.load(open(f"{A.root}/outputs/{A.model}/results.json"))["summary"]
e2, e3 = S["E2_temporal"], S["E3_abstention"]
N_EASY, N_HARD = 3, 4

C_OK, C_BAD, C_DARK = "#2a9d8f", "#e76f51", "#264653"
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))

# ---- left: rejection split by negative type ----
vals = [e3["rejection_acc_easy"], e3["rejection_acc_hard"]]
cnts = [f"{round(vals[0]*N_EASY)} of {N_EASY}", f"{round(vals[1]*N_HARD)} of {N_HARD}"]
bars = axes[0].bar(["easy negatives\n(different procedure)",
                    "hard negatives\n(same objects, absent action)"],
                   vals, 0.55, color=[C_OK, C_BAD])
for b, v, c in zip(bars, vals, cnts):
    axes[0].text(b.get_x() + b.get_width()/2, v + 0.03, f"{v:.2f}\n{c}",
                 ha="center", fontsize=9)
axes[0].set_ylim(0, 1.25)
axes[0].set_ylabel("share of wrong queries refused", fontsize=9.5)
axes[0].set_title("What the system refuses", fontsize=10.5)
axes[0].tick_params(labelsize=8.5)

# ---- right: the cost of being allowed to refuse ----
v = [e2["mean_tIoU"], e3["mean_tIoU"]]
bars = axes[1].bar(["E2\nno refusal allowed", "E3\nrefusal allowed"], v, 0.55,
                   color=[C_DARK, C_DARK])
for b, x in zip(bars, v):
    axes[1].text(b.get_x() + b.get_width()/2, x + 0.008, f"{x:.3f}",
                 ha="center", fontsize=9.5)
axes[1].set_ylim(0, max(v) * 1.45)
axes[1].set_ylabel("mean time overlap on the six real actions", fontsize=9.5)
axes[1].set_title("What it costs", fontsize=10.5)
axes[1].tick_params(labelsize=8.5)
axes[1].annotate(f"identical: {e3['false_abstain_on_positives']} of 6 real actions\n"
                 "were wrongly refused",
                 xy=(1, v[1]), xytext=(0.42, max(v) * 1.30), ha="center", fontsize=8.5,
                 arrowprops=dict(arrowstyle="->", lw=0.9, color="0.35", shrinkB=22))

fig.suptitle("CLIP ViT-L/14: refusing to answer was free for the best model, "
             "but it catches only the easy cases", fontsize=10.5, y=1.0)
fig.tight_layout()
os.makedirs(os.path.dirname(os.path.abspath(A.out)), exist_ok=True)
fig.savefig(A.out, dpi=170, bbox_inches="tight")
print("WROTE", A.out)

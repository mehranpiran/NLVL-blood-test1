#!/usr/bin/env python3
"""
NLVL pilot - step 5: the oppositional-pair analysis.

A frozen vision-language model can easily tell a blood draw from an MRI scan.
The question this pilot asks is whether it can tell an action from its OPPOSITE,
when both descriptions contain the same objects. This script measures that and
draws it.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
MODELS = ["clip", "clip_l14", "clip_l14_squash", "clip_l14_zoom", "biomedclip"]
NICE = {"clip": "CLIP ViT-B/32", "clip_l14": "CLIP ViT-L/14",
        "clip_l14_squash": "CLIP ViT-L/14\n(squash)", "clip_l14_zoom": "CLIP ViT-L/14\n(zoom)",
        "biomedclip": "BioMedCLIP\nViT-B/16"}


def curves(m):
    z = np.load(f"{ROOT}/outputs/{m}/scores.npz", allow_pickle=True)
    return z["S_smooth"], list(z["query_ids"]), z["times"]


def main():
    rows = []
    for m in MODELS:
        if not os.path.exists(f"{ROOT}/outputs/{m}/scores.npz"):
            continue
        S, qid, _ = curves(m)
        g = lambda a, b: float(np.corrcoef(S[qid.index(a)], S[qid.index(b)])[0, 1])
        d = lambda a, b: int(abs(np.argmax(S[qid.index(a)]) - np.argmax(S[qid.index(b)])))
        rows.append({"model": m,
                     "r_opposite": g("p3", "h3"), "peak_dist_opposite": d("p3", "h3"),
                     "r_unrelated": g("p3", "e1"), "peak_dist_unrelated": d("p3", "e1")})
    json.dump(rows, open(f"{ROOT}/outputs/oppositional_analysis.json", "w"), indent=2)

    # ---- bar chart ----
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(rows)); w = 0.36
    ax.bar(x - w/2, [r["r_opposite"] for r in rows], w, color="#c1121f",
           label='opposite action\n"inserts" vs "pulls out"')
    ax.bar(x + w/2, [r["r_unrelated"] for r in rows], w, color="#8ecae6",
           label='unrelated action\n"inserts needle" vs "MRI scanner"')
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([NICE[r["model"]] for r in rows], fontsize=8.5)
    ax.set_ylabel("correlation between the two score curves", fontsize=9.5)
    ax.set_title("A frozen model separates different procedures easily, "
                 "but not an action from its opposite", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    ax.set_ylim(-0.3, 1.15)
    for i, r in enumerate(rows):
        ax.text(i - w/2, r["r_opposite"] + 0.03, f'{r["r_opposite"]:.2f}',
                ha="center", fontsize=8)
        ax.text(i + w/2, r["r_unrelated"] + 0.03, f'{r["r_unrelated"]:.2f}',
                ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{ROOT}/figures/fig5_oppositional_separation.png", dpi=170)
    plt.close(fig)

    # ---- the paired curve plot, with the unrelated query as a reference ----
    m = "clip_l14"
    S, qid, t = curves(m)
    GT = json.load(open(f"{ROOT}/data/ground_truth.json"))["intervals"]["p3"]
    r = [x for x in rows if x["model"] == m][0]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.axvspan(GT["start"] - .5, GT["end"] + .5, color="#2a9d8f", alpha=0.25, lw=0,
               label="ground truth: the needle is inserted")
    ax.plot(t, S[qid.index("p3")], color="#264653", lw=2.1,
            label='p3  "a nurse inserts the needle into the patient\'s arm"')
    ax.plot(t, S[qid.index("h3")], color="#c1121f", lw=2.1, ls="--",
            label='h3  "a nurse pulls the needle out of the patient\'s arm"  (never happens)')
    ax.plot(t, S[qid.index("e1")], color="#9aa5ab", lw=1.5, ls=":",
            label='e1  "a patient lies inside an MRI scanner"  (reference)')
    ax.set_xlabel("time (s)", fontsize=9.5)
    ax.set_ylabel("cosine similarity", fontsize=9.5)
    ax.set_title(f"{NICE[m]}: the opposite query tracks the true one almost exactly "
                 f"(r = {r['r_opposite']:.2f}, same peak frame)", fontsize=10.5)
    ax.legend(fontsize=8, loc="lower left", framealpha=0.92)
    ax.tick_params(labelsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{ROOT}/figures/fig2b_oppositional_with_reference.png", dpi=170)
    plt.close(fig)

    print(f"{'model':<18}{'r(opposite)':>13}{'r(unrelated)':>14}{'peak dist opp':>15}")
    for r in rows:
        print(f"{r['model']:<18}{r['r_opposite']:>13.3f}{r['r_unrelated']:>14.3f}"
              f"{r['peak_dist_opposite']:>15d}")
    print(f"\nwrote figures/fig5_oppositional_separation.png and "
          f"fig2b_oppositional_with_reference.png")


if __name__ == "__main__":
    main()

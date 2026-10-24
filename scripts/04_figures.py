#!/usr/bin/env python3
"""
NLVL pilot - step 4: figures.

Fig 1  score curves for the positive queries, with ground truth and prediction
Fig 2  the oppositional pair: insert needle vs pull the needle out
Fig 3  effect of temporal smoothing on one query
Fig 4  summary bars across variants and models
"""
import argparse, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
C_GT, C_PR, C_RAW, C_SM = "#2a9d8f", "#e76f51", "#b0b0b0", "#264653"


def band(ax, lo, hi, color, label, alpha=0.22):
    ax.axvspan(lo - 0.5, hi + 0.5, color=color, alpha=alpha, lw=0, label=label)


def load(root, model):
    out = f"{root}/outputs/{model}"
    z = np.load(f"{out}/scores.npz", allow_pickle=True)
    R = json.load(open(f"{out}/results.json"))
    qs = json.load(open(f"{root}/data/queries.json"))["queries"]
    GT = json.load(open(f"{root}/data/ground_truth.json"))["intervals"]
    return z, R, {q["id"]: q for q in qs}, GT, list(z["query_ids"]), out


def fig1(z, R, Q, GT, qid, out, model):
    pos = [q for q in qid if Q[q]["type"] == "positive"]
    fig, axes = plt.subplots(len(pos), 1, figsize=(10, 1.75 * len(pos)), sharex=True)
    S = z["S_smooth"]; t = z["times"]
    for ax, q in zip(np.atleast_1d(axes), pos):
        k = qid.index(q)
        ax.plot(t, S[k], color=C_SM, lw=1.8)
        band(ax, GT[q]["start"], GT[q]["end"], C_GT, "ground truth")
        pr = R["per_query"]["E2_temporal"][q]["pred"]
        if pr[0] is not None:
            band(ax, pr[0], pr[1], C_PR, "prediction")
        iou = R["per_query"]["E2_temporal"][q]["tIoU"]
        ax.set_ylabel(Q[q]["name"].replace("_", "\n"), fontsize=8)
        ax.text(0.995, 0.86, f"tIoU {iou:.3f}", transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.5))
        ax.tick_params(labelsize=8)
    np.atleast_1d(axes)[-1].set_xlabel("time (s)", fontsize=9)
    np.atleast_1d(axes)[0].legend(fontsize=8, loc="upper left", ncol=2, framealpha=0.85)
    fig.suptitle(f"{model}: smoothed similarity, ground truth and prediction",
                 fontsize=11, y=0.998)
    fig.tight_layout()
    fig.savefig(f"{out}/fig1_positive_curves.png", dpi=170)
    plt.close(fig)


def fig2(z, R, Q, GT, qid, out, model):
    """The headline figure: a true action and its oppositional hard negative."""
    S = z["S_smooth"]; t = z["times"]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for q, col, ls in (("p3", "#264653", "-"), ("h3", "#c1121f", "--")):
        k = qid.index(q)
        ax.plot(t, S[k], color=col, lw=2.0, ls=ls,
                label=f'{Q[q]["id"]}  "{Q[q]["text"]}"')
    band(ax, GT["p3"]["start"], GT["p3"]["end"], C_GT,
         "ground truth: needle is inserted")
    for q, col in (("p3", "#264653"), ("h3", "#c1121f")):
        pr = R["per_query"]["E2_temporal"][q]["pred"]
        if pr[0] is not None:
            ax.axvspan(pr[0] - .5, pr[1] + .5, color=col, alpha=0.10, lw=0)
            ax.annotate("", xy=(pr[0] - .5, ax.get_ylim()[0]),
                        xytext=(pr[1] + .5, ax.get_ylim()[0]))
    ax.set_xlabel("time (s)", fontsize=9.5)
    ax.set_ylabel("cosine similarity", fontsize=9.5)
    ax.set_title(f"{model}: the needle is never withdrawn in this video, yet the "
                 "opposite query peaks in the same place", fontsize=10.5)
    ax.legend(fontsize=8.5, loc="lower right", framealpha=0.9)
    ax.tick_params(labelsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{out}/fig2_oppositional_pair.png", dpi=170)
    plt.close(fig)


def fig3(z, R, Q, GT, qid, out, model, q="p1"):
    t = z["times"]; k = qid.index(q)
    fig, ax = plt.subplots(figsize=(10, 3.0))
    ax.plot(t, z["S_raw"][k], color=C_RAW, lw=1.5, label="raw, frame by frame")
    ax.plot(t, z["S_smooth"][k], color=C_SM, lw=2.2, label="after temporal smoothing")
    band(ax, GT[q]["start"], GT[q]["end"], C_GT, "ground truth")
    ax.set_xlabel("time (s)", fontsize=9.5); ax.set_ylabel("cosine similarity", fontsize=9.5)
    ax.set_title(f'{model}: effect of temporal smoothing on "{Q[q]["text"]}"', fontsize=10.5)
    ax.legend(fontsize=8.5, framealpha=0.9); ax.tick_params(labelsize=8.5)
    fig.tight_layout()
    fig.savefig(f"{out}/fig3_smoothing_effect.png", dpi=170)
    plt.close(fig)


def fig4(root, models, out):
    variants = ["E1_baseline", "E2_temporal", "E3_abstention"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    w = 0.8 / len(models)
    for mi, m in enumerate(models):
        f = f"{root}/outputs/{m}/results.json"
        if not os.path.isfile(f):
            continue
        s = json.load(open(f))["summary"]
        x = np.arange(len(variants)) + mi * w
        axes[0].bar(x, [s[v]["mean_tIoU"] for v in variants], w, label=m)
        axes[1].bar(x, [s[v]["rejection_acc_all_neg"] for v in variants], w, label=m)
    for ax, ttl, yl in ((axes[0], "localisation accuracy", "mean tIoU"),
                        (axes[1], "rejection of absent actions", "rejection accuracy")):
        ax.set_xticks(np.arange(len(variants)) + 0.4 - w / 2)
        ax.set_xticklabels([v.replace("_", "\n") for v in variants], fontsize=8.5)
        ax.set_title(ttl, fontsize=10.5); ax.set_ylabel(yl, fontsize=9.5)
        ax.tick_params(labelsize=8.5); ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{out}/fig4_summary.png", dpi=170)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip_l14")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--all-models", nargs="*", default=None)
    a = ap.parse_args()
    z, R, Q, GT, qid, out = load(a.root, a.model)
    fig1(z, R, Q, GT, qid, out, a.model)
    fig2(z, R, Q, GT, qid, out, a.model)
    fig3(z, R, Q, GT, qid, out, a.model)
    fig_dir = f"{a.root}/figures"
    os.makedirs(fig_dir, exist_ok=True)
    if a.all_models:
        fig4(a.root, a.all_models, fig_dir)
    for f in ("fig1_positive_curves", "fig2_oppositional_pair", "fig3_smoothing_effect"):
        src, dst = f"{out}/{f}.png", f"{fig_dir}/{a.model}_{f}.png"
        if os.path.isfile(src):
            import shutil; shutil.copyfile(src, dst)
    print(f"[{a.model}] figures written to {out} and copied to {fig_dir}")


if __name__ == "__main__":
    main()

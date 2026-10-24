#!/usr/bin/env python3
"""
NLVL pilot - does finer temporal sampling recover action direction?

The endpoint statistic d = f(last) - f(first) is the telescoping sum of the local
steps, so mean_t df(t) points the same way and sampling rate cannot change it.
Two statistics that DO depend on the sampling rate are used instead:

  step_vote  : the fraction of consecutive steps that move along the caption
               direction, mapped to [-1, 1]. Order-sensitive and non-linear, so
               it is not a telescoping sum.
  step_mean  : the mean of the per-step projections normalised per step, which
               weights many small consistent movements more than one large jump.

Both flip sign exactly under time reversal, so a reversed clip is still handled
automatically and no extra labels are needed.
"""
import argparse, glob, json, os
from math import comb
import numpy as np
import torch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
os.environ.setdefault("HF_HOME", f"{ROOT}/models/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

PAIRS = {
 "px6290525_B_blood_extraction_close_up": (
    "blood is being drawn out of the arm into the syringe",
    "blood is being pushed out of the syringe into the arm"),
 "px6290530_B_a_medical_professional_using_a_tourniquet_on": (
    "a tourniquet is being tied around the arm",
    "a tourniquet is being untied and taken off the arm"),
 "px8460350_A_putting_band_aid_on_a_persons_arm": (
    "a plaster is being put onto the arm",
    "a plaster is being peeled off the arm"),
 "v13_video_of_venipuncture_blood_draw_or_collection_u": (
    "the test tube is filling up with blood",
    "the test tube is emptying of blood"),
}


def binom_p(k, n, p=0.5):
    pr = [comb(n, i) * p**i * (1-p)**(n-i) for i in range(n+1)]
    return min(1.0, sum(q for q in pr if q <= pr[k] * (1 + 1e-9)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps_dir", default="frames_4fps")
    ap.add_argument("--model", default="clip_l14")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()

    from transformers import CLIPModel, CLIPProcessor
    mid = {"clip": "openai/clip-vit-base-patch32",
           "clip_l14": "openai/clip-vit-large-patch14"}[a.model]
    model = CLIPModel.from_pretrained(mid).eval()
    proc = CLIPProcessor.from_pretrained(mid)
    def fe(o): return o.pooler_output if hasattr(o, "pooler_output") else o

    texts = [t for k in PAIRS for t in PAIRS[k]]
    with torch.no_grad():
        T = fe(model.get_text_features(**proc(text=texts, return_tensors="pt",
                                              padding=True, truncation=True))).float().numpy()
    T = T / np.linalg.norm(T, axis=1, keepdims=True)

    print(f"{'clip':<40}{'n':>5}{'endpoint':>11}{'step_vote':>11}{'step_mean':>11}")
    print("-" * 78)
    rows = []
    for i, (name, (fwd, rev)) in enumerate(PAIRS.items()):
        fr = sorted(glob.glob(f"{a.root}/corpus/{a.fps_dir}/{name}/*.jpg"))
        if not fr:
            print(f"  !! no frames for {name}"); continue
        V = []
        with torch.no_grad():
            for k in range(0, len(fr), 32):
                ims = [Image.open(p).convert("RGB") for p in fr[k:k+32]]
                V.append(fe(model.get_image_features(
                    **proc(images=ims, return_tensors="pt"))).float())
        F = torch.cat(V).numpy()
        F = F / np.linalg.norm(F, axis=1, keepdims=True)
        u = T[2*i] - T[2*i+1]; u = u / np.linalg.norm(u)

        endpoint = float((F[-1] - F[0]) @ u / (np.linalg.norm(F[-1] - F[0]) + 1e-12))
        steps = np.diff(F, axis=0)
        sn = np.linalg.norm(steps, axis=1, keepdims=True) + 1e-12
        proj = (steps / sn) @ u
        step_vote = float(np.sign(proj).mean())
        step_mean = float(proj.mean())
        rows.append({"clip": name, "n_frames": len(fr), "endpoint": endpoint,
                     "step_vote": step_vote, "step_mean": step_mean})
        print(f"{name[:38]:<40}{len(fr):>5}{endpoint:>11.4f}{step_vote:>11.4f}{step_mean:>11.4f}")

    print("-" * 78)
    for stat in ("endpoint", "step_vote", "step_mean"):
        k = sum(r[stat] > 0 for r in rows); n = len(rows)
        print(f"{stat:<12} correct {k}/{n}  (binomial p = {binom_p(k, n):.3f})")
    json.dump(rows, open(f"{a.root}/corpus/emb/{a.model}/fps_check_{a.fps_dir}.json", "w"),
              indent=1)
    print(f"\nwrote fps_check_{a.fps_dir}.json")


if __name__ == "__main__":
    main()

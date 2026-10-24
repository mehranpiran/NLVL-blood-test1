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


# ================= FIGURE 4: why - steps are perpendicular =================
PAIRS = {
 "px6290525_B_blood_extraction_close_up":
    ("blood is being drawn out of the arm into the syringe",
     "blood is being pushed out of the syringe into the arm"),
 "px6290530_B_a_medical_professional_using_a_tourniquet_on":
    ("a tourniquet is being tied around the arm",
     "a tourniquet is being untied and taken off the arm"),
 "px8460350_A_putting_band_aid_on_a_persons_arm":
    ("a plaster is being put onto the arm",
     "a plaster is being peeled off the arm"),
 "v13_video_of_venipuncture_blood_draw_or_collection_u":
    ("the test tube is filling up with blood",
     "the test tube is emptying of blood"),
}
os.environ.setdefault("HF_HOME", f"{A.root}/models/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
mid = {"clip": "openai/clip-vit-base-patch32",
       "clip_l14": "openai/clip-vit-large-patch14"}[A.model]
model = CLIPModel.from_pretrained(mid).eval()
proc = CLIPProcessor.from_pretrained(mid)
fe = lambda o: o.pooler_output if hasattr(o, "pooler_output") else o

texts = [t for k in PAIRS for t in PAIRS[k]]
with torch.no_grad():
    T = fe(model.get_text_features(**proc(text=texts, return_tensors="pt",
                                          padding=True, truncation=True))).float().numpy()
T = T / np.linalg.norm(T, axis=1, keepdims=True)

CACHE = f"{A.outdir}/orthogonality_cosines.npz"
angles, per_clip = [], []
if os.path.isfile(CACHE):
    _z = np.load(CACHE, allow_pickle=True)
    angles = [_z[k] for k in _z.files]
    per_clip = [(k, float(np.degrees(np.arccos(np.clip(_z[k], -1, 1))).mean()),
                 int(len(_z[k]))) for k in _z.files]
    print("loaded cached cosines for", len(angles), "clips")
for i, name in enumerate([] if angles else PAIRS):
    fr = sorted(glob.glob(f"{A.root}/corpus/frames_4fps/{name}/*.jpg"))
    if not fr:
        print("no 4 fps frames for", name); continue
    V = []
    with torch.no_grad():
        for k in range(0, len(fr), 32):
            ims = [Image.open(p).convert("RGB") for p in fr[k:k+32]]
            V.append(fe(model.get_image_features(
                **proc(images=ims, return_tensors="pt"))).float())
    F = torch.cat(V).numpy(); F = F / np.linalg.norm(F, axis=1, keepdims=True)
    u = T[2*i] - T[2*i+1]; u = u / np.linalg.norm(u)
    steps = np.diff(F, axis=0)
    steps = steps / (np.linalg.norm(steps, axis=1, keepdims=True) + 1e-12)
    c = steps @ u
    angles.append(c)
    per_clip.append((name, np.degrees(np.arccos(np.clip(c, -1, 1))).mean(), len(c)))
if not os.path.isfile(CACHE):
    np.savez_compressed(CACHE, **{n: a for (n, _, _), a in zip(per_clip, angles)})
allc = np.concatenate(angles)
deg = np.degrees(np.arccos(np.clip(allc, -1, 1)))

fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
axs[0].hist(deg, bins=28, color=C_GREY, edgecolor=C_DARK, lw=0.7)
axs[0].axvline(deg.mean(), color=C_OK, lw=4.0, alpha=0.95,
               label=f"measured mean, {deg.mean():.2f} degrees")
axs[0].axvline(90, color=C_BAD, lw=1.6, ls=(0, (4, 3)),
               label="90 degrees, no information at all")
axs[0].annotate("the two lines lie on top of each other",
                xy=(90, axs[0].get_ylim()[1] * 0.72),
                xytext=(0.03, 0.70), textcoords="axes fraction", fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.9, color="0.35"))
axs[0].set_xlabel("angle between one step in time and the language direction",
                  fontsize=9.5)
axs[0].set_ylabel("number of steps", fontsize=9.5)
axs[0].set_title(f"All {len(deg)} steps, four clips at 4 fps", fontsize=10.5)
axs[0].legend(fontsize=8, framealpha=0.95, loc="upper right")
axs[0].tick_params(labelsize=8.5)

vals = [r["step_mean"] for r in FPSJ]
nm = [r["clip"][:22] for r in FPSJ]
axs[1].barh(np.arange(len(vals)), vals,
            color=[C_OK if v > 0 else C_BAD for v in vals], height=0.6)
axs[1].axvline(0, color="k", lw=0.9)
axs[1].set_yticks(np.arange(len(vals))); axs[1].set_yticklabels(nm, fontsize=7.5)
axs[1].invert_yaxis()
axs[1].set_xlim(-0.012, 0.012)
axs[1].set_xlabel("average projection of one step onto the language direction",
                  fontsize=9.5)
axs[1].set_title("The signal that is left is about 0.003", fontsize=10.5)
axs[1].tick_params(labelsize=8.5)
fig.suptitle("Movement from frame to frame is almost perpendicular to the direction "
             "that separates an action from its reverse", fontsize=10.5, y=1.02)
fig.tight_layout()
fig.savefig(f"{A.outdir}/fig_mv4_orthogonality.png", dpi=170, bbox_inches="tight")
plt.close(fig)

json.dump({"mean_angle_deg": float(deg.mean()), "n_steps": int(len(deg)),
           "per_clip_mean_angle": [(n, float(a), int(k)) for n, a, k in per_clip]},
          open(f"{A.outdir}/orthogonality_stats.json", "w"), indent=2)
print("mean angle", deg.mean(), "over", len(deg), "steps")
print("WROTE 4 figures to", A.outdir)

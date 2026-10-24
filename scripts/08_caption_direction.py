#!/usr/bin/env python3
"""
NLVL pilot - the language-grounded direction test.

The arrow-of-time test asks whether direction is recoverable at all. This asks
the harder and more useful question: can the model match a clip to the CORRECT
one of two captions that differ only in the direction of the action?

For a clip whose forward action is A and whose reverse is A-bar, the displacement
in embedding space is d = f(last) - f(first). The test statistic is

        score = d . ( text(A) - text(A-bar) )

If the embedding space carries any directional information that is aligned with
language, this is positive for the forward clip. Reversing the clip negates d and
therefore negates the score, so the reversed clip is handled automatically and
contributes no extra information. There is NO training here at all.
"""
import argparse, json, os
from math import comb
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root

# Per-clip directional labels.
#   verified = the action was confirmed by inspecting the clip's frames
#   title    = taken from the depositor's own title, which states the action
PAIRS = {
 "px6290525_B_blood_extraction_close_up": dict(
    fwd="blood is being drawn out of the arm into the syringe",
    rev="blood is being pushed out of the syringe into the arm", src="verified"),
 # px6290542 ("blood being collected in test tube") was DROPPED after inspection:
 # the tube filling is not clearly visible and the clip ends with the needle being
 # removed and a cotton pad applied, so the depositor's title does not describe the
 # dominant change across the clip. Labelling it either way would be a guess.
 "v13_video_of_venipuncture_blood_draw_or_collection_u": dict(
    fwd="the test tube is filling up with blood",
    rev="the test tube is emptying of blood", src="verified"),
 "px8460351_A_a_person_having_a_blood_examination": dict(
    fwd="the test tube is filling up with blood",
    rev="the test tube is emptying of blood", src="verified"),
 "px8460350_A_putting_band_aid_on_a_persons_arm": dict(
    fwd="a plaster is being put onto the arm",
    rev="a plaster is being peeled off the arm", src="title"),
 "px6290532_B_nurse_putting_a_band_aid_on_patient_arm": dict(
    fwd="a plaster is being put onto the arm",
    rev="a plaster is being peeled off the arm", src="title"),
 "px6290530_B_a_medical_professional_using_a_tourniquet_on": dict(
    fwd="a tourniquet is being tied around the arm",
    rev="a tourniquet is being untied and taken off the arm", src="verified"),
}


def binom_p(k, n, p=0.5):
    pr = [comb(n, i) * p**i * (1-p)**(n-i) for i in range(n+1)]
    return min(1.0, sum(q for q in pr if q <= pr[k] * (1 + 1e-9)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip_l14")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args()
    emb = f"{a.root}/corpus/emb/{a.model}"
    Z = np.load(f"{emb}/corpus_frames.npz")
    IDX = {r["name"]: r for r in json.load(open(f"{emb}/corpus_index.json"))}

    os.environ.setdefault("HF_HOME", f"{a.root}/models/hf_cache")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    from transformers import CLIPModel, CLIPProcessor
    mid = {"clip": "openai/clip-vit-base-patch32",
           "clip_l14": "openai/clip-vit-large-patch14"}[a.model]
    model = CLIPModel.from_pretrained(mid).eval()
    proc = CLIPProcessor.from_pretrained(mid)

    texts, keys = [], []
    for k, v in PAIRS.items():
        if k in Z: texts += [v["fwd"], v["rev"]]; keys.append(k)
    with torch.no_grad():
        inp = proc(text=texts, return_tensors="pt", padding=True, truncation=True)
        o = model.get_text_features(**inp)
        T = (o.pooler_output if hasattr(o, "pooler_output") else o).float().numpy()
    T = T / np.linalg.norm(T, axis=1, keepdims=True)

    print(f"{'clip':<46}{'shoot':>6}{'src':>10}{'score':>11}{'ok':>5}")
    print("-" * 78)
    res, ok_n = [], 0
    for i, k in enumerate(keys):
        F = Z[k]
        d = F[-1] - F[0]
        nd = np.linalg.norm(d)
        if nd < 1e-9: continue
        d = d / nd
        diff = T[2*i] - T[2*i+1]
        diff = diff / np.linalg.norm(diff)
        sc = float(d @ diff)
        ok = sc > 0; ok_n += ok
        res.append({"clip": k, "shoot": IDX[k]["shoot"], "src": PAIRS[k]["src"],
                    "score": sc, "correct": bool(ok)})
        print(f"{k[:44]:<46}{IDX[k]['shoot']:>6}{PAIRS[k]['src']:>10}"
              f"{sc:>11.4f}{'  Y' if ok else '  n':>5}")
    n = len(res)
    print("-" * 78)
    print(f"zero-shot direction accuracy: {ok_n}/{n} = {ok_n/n:.3f}  "
          f"(chance 0.500, exact binomial p = {binom_p(ok_n, n):.4f})")
    ver = [r for r in res if r["src"] == "verified"]
    if ver:
        kv = sum(r["correct"] for r in ver)
        print(f"  restricted to hand-verified clips only: {kv}/{len(ver)}")
    json.dump({"model": a.model, "n": n, "correct": ok_n,
               "acc": ok_n/n, "binomial_p": binom_p(ok_n, n), "per_clip": res},
              open(f"{emb}/caption_direction.json", "w"), indent=1)
    print(f"\nwrote {emb}/caption_direction.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NLVL pilot - encode the multi-video corpus with a frozen model.

Each clip's frames are encoded once and stored as an ordered sequence. Time
reversal is then obtained by reversing the sequence, which is exactly equivalent
to playing the clip backwards at this sampling rate, so no clip has to be
re-encoded or re-rendered.
"""
import argparse, glob, json, os, time
import numpy as np
import torch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
os.environ.setdefault("HF_HOME", f"{ROOT}/models/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODELS = {"clip": "openai/clip-vit-base-patch32",
          "clip_l14": "openai/clip-vit-large-patch14"}


def feat(o):
    return o.pooler_output if hasattr(o, "pooler_output") else o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip_l14", choices=sorted(MODELS))
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args()

    from transformers import CLIPModel, CLIPProcessor
    mid = MODELS[a.model]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(mid).to(dev).eval()
    proc = CLIPProcessor.from_pretrained(mid)

    cur = json.load(open(f"{a.root}/corpus/manifest/curated.json"))["included"]
    out = f"{a.root}/corpus/emb/{a.model}"
    os.makedirs(out, exist_ok=True)

    store, t0 = {}, time.time()
    for i, r in enumerate(cur, 1):
        fr = sorted(glob.glob(f"{a.root}/corpus/frames/{r['name']}/*.jpg"))
        if not fr:
            print(f"  !! no frames for {r['name']}"); continue
        vecs = []
        with torch.no_grad():
            for k in range(0, len(fr), a.batch):
                ims = [Image.open(p).convert("RGB") for p in fr[k:k + a.batch]]
                inp = proc(images=ims, return_tensors="pt").to(dev)
                vecs.append(feat(model.get_image_features(**inp)).float().cpu())
        F = torch.cat(vecs).numpy()
        F = F / np.linalg.norm(F, axis=1, keepdims=True)
        store[r["name"]] = F.astype(np.float32)
        print(f"  [{i:2d}/{len(cur)}] {r['name'][:48]:<48} {F.shape[0]:3d} frames "
              f"({time.time()-t0:.0f}s)")

    np.savez_compressed(f"{out}/corpus_frames.npz", **store)
    meta = [{"name": r["name"], "shoot": r["shoot"], "video_id": r["video_id"],
             "title": r["title"], "n_frames": int(store[r["name"]].shape[0])}
            for r in cur if r["name"] in store]
    json.dump(meta, open(f"{out}/corpus_index.json", "w"), indent=1)
    print(f"\n[{a.model}] {len(store)} clips, "
          f"{sum(v.shape[0] for v in store.values())} frames -> {out}/corpus_frames.npz")


if __name__ == "__main__":
    main()

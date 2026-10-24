#!/usr/bin/env python3
"""
NLVL pilot - step 1: encode frames and queries with a frozen vision-language model.

Nothing is trained here. The model weights are loaded once, used in eval mode under
torch.no_grad(), and the resulting embeddings are written to disk so that every later
experiment reuses them instead of recomputing them.

Usage:  python 01_encode.py --model clip
        python 01_encode.py --model biomedclip
"""
import argparse, json, os, sys, time
import numpy as np
import torch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
os.environ.setdefault("HF_HOME", f"{ROOT}/models/hf_cache")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

MODELS = {
    "clip":       {"backend": "hf",       "id": "openai/clip-vit-base-patch32"},
    "clip_l14":   {"backend": "hf",       "id": "openai/clip-vit-large-patch14"},
    "biomedclip": {"backend": "open_clip",
                   "id": "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"},
}


def load_frames(frames_dir, frames_csv):
    import csv
    rows = []
    with open(frames_csv) as fh:
        for r in csv.DictReader(fh):
            rows.append((int(r["frame_index"]), float(r["timestamp_sec"]), r["filename"]))
    rows.sort()
    paths = [os.path.join(frames_dir, f) for _, _, f in rows]
    times = np.array([t for _, t, _ in rows], dtype=np.float32)
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        sys.exit(f"ERROR: {len(missing)} frame files listed in frames.csv are missing, "
                 f"first is {missing[0]}")
    return paths, times


def prep_image(path, mode):
    """
    CLIP's default processor resizes the shortest edge to 224 and then centre-crops
    224x224. On a 1280x720 frame that keeps only 56% of the width, so the left and
    right thirds of every frame are discarded before the model ever sees them.
      default : leave that behaviour alone
      squash  : resize the whole frame to a square, keeping all content (aspect distorted)
      zoom    : crop a fixed box around the action region, then let the processor resize
    """
    im = Image.open(path).convert("RGB")
    if mode == "default":
        return im
    if mode == "squash":
        return im.resize((im.size[1], im.size[1]), Image.LANCZOS)
    if mode == "zoom":
        W, H = im.size
        l, t, r, b = 0.18, 0.05, 0.88, 0.95       # action region, measured from the frames
        return im.crop((int(l*W), int(t*H), int(r*W), int(b*H)))
    raise ValueError(mode)


def _feat(out):
    """transformers 4.x returns a tensor from get_*_features; 5.x returns an
    output object whose pooler_output holds the projected joint-space vector."""
    if hasattr(out, "pooler_output"):
        return out.pooler_output
    if hasattr(out, "last_hidden_state") and not torch.is_tensor(out):
        raise RuntimeError("get_*_features returned no pooler_output")
    return out


def encode_hf(model_id, paths, texts, device, batch=32, preproc="default"):
    from transformers import CLIPModel, CLIPProcessor
    model = CLIPModel.from_pretrained(model_id).to(device).eval()
    proc = CLIPProcessor.from_pretrained(model_id)
    img = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            ims = [prep_image(p, preproc) for p in paths[i:i + batch]]
            inp = proc(images=ims, return_tensors="pt").to(device)
            img.append(_feat(model.get_image_features(**inp)).float().cpu())
        inp = proc(text=texts, return_tensors="pt", padding=True, truncation=True).to(device)
        txt = _feat(model.get_text_features(**inp)).float().cpu()
    return torch.cat(img).numpy(), txt.numpy()


def encode_open_clip(model_id, paths, texts, device, batch=32, preproc="default"):
    import open_clip
    model, _, preprocess = open_clip.create_model_and_transforms(model_id)
    tokenizer = open_clip.get_tokenizer(model_id)
    model = model.to(device).eval()
    img = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            ims = torch.stack([preprocess(prep_image(p, preproc))
                               for p in paths[i:i + batch]]).to(device)
            img.append(model.encode_image(ims).float().cpu())
        txt = model.encode_text(tokenizer(texts).to(device)).float().cpu()
    return torch.cat(img).numpy(), txt.numpy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="clip", choices=sorted(MODELS))
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--preproc", default="default", choices=["default", "squash", "zoom"])
    ap.add_argument("--tag", default=None, help="output subfolder; defaults to the model name")
    a = ap.parse_args()

    spec = MODELS[a.model]
    tag = a.tag or (a.model if a.preproc == "default" else f"{a.model}_{a.preproc}")
    data, out = f"{a.root}/data", f"{a.root}/outputs/{tag}"
    os.makedirs(out, exist_ok=True)

    paths, times = load_frames(f"{data}/frames", f"{data}/frames.csv")
    qs = json.load(open(f"{data}/queries.json"))["queries"]
    texts = [q["text"] for q in qs]
    print(f"[{tag}] {len(paths)} frames, {len(texts)} queries, preproc={a.preproc}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[{tag}] device={device}  backend={spec['backend']}  id={spec['id']}")

    t0 = time.time()
    enc = encode_hf if spec["backend"] == "hf" else encode_open_clip
    img, txt = enc(spec["id"], paths, texts, device, a.batch, a.preproc)
    print(f"[{tag}] encoded in {time.time()-t0:.1f}s  "
          f"img={img.shape} txt={txt.shape}")

    # L2-normalise so that a dot product is exactly the cosine similarity
    img = img / np.linalg.norm(img, axis=1, keepdims=True)
    txt = txt / np.linalg.norm(txt, axis=1, keepdims=True)

    np.savez_compressed(
        f"{out}/embeddings.npz",
        frame_emb=img.astype(np.float32),
        text_emb=txt.astype(np.float32),
        times=times,
        query_ids=np.array([q["id"] for q in qs]),
    )
    # sanity: embeddings must not be degenerate
    fsd = float(img.std(0).mean())
    print(f"[{tag}] mean per-dim std of frame embeddings = {fsd:.5f}"
          f"{'   <-- WARNING: near-constant embeddings' if fsd < 1e-4 else ''}")
    print(f"[{tag}] wrote {out}/embeddings.npz")


if __name__ == "__main__":
    main()

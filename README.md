# NLVL pilot: natural-language video localisation with frozen CLIP

A small pilot study on **natural-language video localisation (NLVL)**: given a text query
such as *"a nurse inserts the needle into the patient's arm"*, find the time interval in a
video where it happens. **Nothing is trained.** Each model is a frozen image-text encoder
(CLIP ViT-B/32, CLIP ViT-L/14 or BioMedCLIP) that scores the video frame by frame.

The pilot has two parts:

1. **Single-video study.** One continuous 84 s phlebotomy clip with 13 text queries:
   6 positives, 4 hard negatives and 3 easy negatives.
2. **Multi-video time-reversal study.** 21 close-up venipuncture clips (460 frames) from
   11 independent shoots. This part tests whether a frozen CLIP model can tell an action
   apart from its reverse.

## The video

> **Original video:** [*A Person Having a Blood Examination* on Pexels (video 8460351)](https://www.pexels.com/video/a-person-having-a-blood-examination-8460351/)
> (Pexels License, free to use).

The `.mp4` itself is not stored in this repository. **All 84 frames used in the study are
included** in [`data/frames/`](data/frames). They were sampled at 1 fps, and `frame_NNNN.jpg`
is the frame at t = NNNN − 1 seconds (see [`data/frames.csv`](data/frames.csv)). To recreate
them from the original video:

```bash
ffmpeg -i pexels_8460351.mp4 -vf fps=1 -q:v 2 data/frames/frame_%04d.jpg
```

The ground truth in [`data/ground_truth.json`](data/ground_truth.json) was annotated from
the video itself. The frame sheets used as evidence are in
[`figures/annotation_evidence/`](figures/annotation_evidence).

## Key findings

### Single video (mean tIoU over the 6 positive queries)

| Model | Baseline | + temporal smoothing | + abstention |
|---|---|---|---|
| CLIP ViT-B/32 | 0.018 | 0.036 | 0.000 |
| CLIP ViT-L/14 | 0.079 | **0.265** | **0.265** |
| BioMedCLIP | 0.052 | 0.098 | 0.098 |

- **Encoder size dominates.** ViT-B/32 stays at chance, while ViT-L/14 reaches 0.265.
- **Temporal smoothing is the largest method gain** (0.079 → 0.265), but it only helps
  once the encoder is strong enough.
- **Abstention costs nothing.** On ViT-L/14 it loses no accuracy on positives, rejects 100%
  of easy negatives and rejects 25% of hard negatives.
- **Central finding: the model is blind to opposite actions.** The score curves for
  *"inserts the needle"* and *"pulls the needle out"* correlate at r = 0.97 and peak on the
  same frame. For comparison, *"inserts the needle"* and *"MRI scanner"* correlate at
  r = 0.06. BioMedCLIP is the only model that separates the pair at all (r = 0.77), and it
  is weak at localisation ([`outputs/oppositional_analysis.json`](outputs/oppositional_analysis.json)).

### Multi-video time reversal

- **A firm positive result.** A frozen image-text model with symmetric temporal filtering is
  *time-reversal equivariant*: playing a clip backwards produces the same scores in reverse
  order. Such a model therefore scores exactly 50% on action direction **by construction**.
  Checked numerically, the largest difference between forward and reversed scores is
  1.19e-07 over 21 clips.
- **Three simple fixes, all null:**
  - shared direction of progress, leave-one-shoot-out: 12/21 (p = 0.66)
  - zero-shot caption direction: 2/6 (p = 0.69)
  - order-sensitive statistics at 4 fps: 2/4, 1/4 and 2/4 (all n.s.)
- **The motion signal is orthogonal to the direction axis.** Frame-to-frame motion projects
  onto the caption direction axis at only ~0.003, and the mean angle is 90.0°. There is no
  weak signal to amplify.
- **Conclusion.** Action direction cannot be read linearly from frozen CLIP frame
  embeddings. A motion-aware or video-native encoder is needed.

## Important notes

- **Tourniquet queries are hard negatives.** The tourniquet is already tied at t = 0 and
  still tied at t = 83 s. It is never applied or removed on camera.
- **Two blood tubes.** Blood is collected into two tubes: the first fills from 45 to 72 s,
  and the second is attached at ~76 s and fills at ~82 s. Only the first fill is annotated.
  The second is recorded as a known ambiguity.
- **Resolution.** The proposal says 1080p, but Pexels serves this clip at 1280×720. This does
  not affect the method, because CLIP resizes every frame to 224×224.
- **Screening the multi-video corpus took the most effort.** Video titles are often
  misleading: one called "blood being collected in test tube" actually ends with needle
  removal. So every candidate clip was checked frame by frame
  ([`corpus/manifest/screening.md`](corpus/manifest/screening.md)).
- **Leave-one-shoot-out evaluation.** Clips from the same shoot are near-duplicates, so the
  multi-video study holds out whole shoots, not single clips.
- **Telescoping-sum trap.** `f(last) − f(first)` is the sum of all the local steps, so the
  mean frame-to-frame difference points the same way at any sampling rate. Testing it at a
  higher fps would show "no change" that looks like evidence but isn't. The 4 fps check
  uses non-linear trajectory statistics instead.

## Multi-video corpus sources

Frames for every clip are in [`corpus/frames/`](corpus/frames) (1 fps) and
[`corpus/frames_4fps/`](corpus/frames_4fps). The full list is in
[`corpus/manifest/curated.json`](corpus/manifest/curated.json). All clips are freely licensed.

| Shoot | Source | Title | Length |
|---|---|---|---|
| D | [Pexels 13149047](https://www.pexels.com/video/13149047/) | close up view of preparing for blood donatio… | 12 s |
| C | [Pexels 14939573](https://www.pexels.com/video/14939573/) | a patient having medical examination | 10 s |
| C | [Pexels 14939577](https://www.pexels.com/video/14939577/) | nurse wiping a patients arm | 8 s |
| C | [Pexels 14939585](https://www.pexels.com/video/14939585/) | tourniquet on persons arm | 7 s |
| C | [Pexels 14939586](https://www.pexels.com/video/14939586/) | nurse taking a patients blood sample | 8 s |
| C | [Pexels 14939592](https://www.pexels.com/video/14939592/) | nurse doing a medical procedure on a patient | 8 s |
| H | [Pexels 28653976](https://www.pexels.com/video/28653976/) | intravenous injection in medical setting | 12 s |
| I | [Pexels 34599556](https://www.pexels.com/video/34599556/) | medical procedure with syringe and gloves | 31 s |
| E | [Pexels 6036689](https://www.pexels.com/video/6036689/) | close up shot of a hand of a man getting blo… | 13 s |
| B | [Pexels 6290525](https://www.pexels.com/video/6290525/) | blood extraction close up | 32 s |
| B | [Pexels 6290530](https://www.pexels.com/video/6290530/) | a medical professional using a tourniquet on… | 20 s |
| B | [Pexels 6290532](https://www.pexels.com/video/6290532/) | nurse putting a band aid on patient arm | 24 s |
| B | [Pexels 6290537](https://www.pexels.com/video/6290537/) | a medical practitioner drawing blood from a… | 13 s |
| B | [Pexels 6290539](https://www.pexels.com/video/6290539/) | a nurse wiping a patients arm | 19 s |
| B | [Pexels 6290542](https://www.pexels.com/video/6290542/) | blood being collected in test tube | 24 s |
| G | [Pexels 6687719](https://www.pexels.com/video/6687719/) | person inserting a dextrose injection on a p… | 21 s |
| A | [Pexels 8460350](https://www.pexels.com/video/8460350/) | putting band aid on a persons arm | 21 s |
| A | [Pexels 8460351](https://www.pexels.com/video/8460351/) | a person having a blood examination | 84 s |
| W1 | Wikimedia Commons | blood_draw_16_second (webm) | 16 s |
| W2 | Wikimedia Commons | video_of_venipuncture_blood_draw_or_collection_u… (BD Vacutainer, webm) | 15 s |
| W3 | Wikimedia Commons | "Анализ крови забор" (mpg) | 62 s |

## Repository layout

```
scripts/      01_encode → 02_localise → 03_evaluate → 04_figures → 05_oppositional
              (single video, run_all.sh runs all of them); 06–09 the multi-video study;
              10, 11* figures; make_*/add_*/fix_*/patch_* build the .docx reports
data/         frames/ (84 frames), frames.csv, queries.json, ground_truth.json, source.txt
outputs/      per model: embeddings.npz, scores.npz, predictions.json, results.json, figures
corpus/       multi-video frames, embeddings (emb/clip_l14) and manifests
figures/      all figures, including annotation_evidence/ and multivideo/
docs/         proposal and results reports (.docx)
```

## Reproducing

Every script finds the repository root by itself, so no paths need editing.

```bash
pip install torch open_clip_torch transformers pillow numpy matplotlib python-docx
bash scripts/run_all.sh                 # single-video study, end to end
PY=/path/to/python bash scripts/run_all.sh   # use a specific interpreter
```

The models are downloaded on first use into `models/hf_cache/`. Everything runs on CPU:
about 30 s for ViT-B/32 and about 150 s for ViT-L/14.

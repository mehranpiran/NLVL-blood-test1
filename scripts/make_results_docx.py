#!/usr/bin/env python3
"""Build the NLVL pilot results report."""
import json, os, datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
OUT = f"{ROOT}/docs/NLVL_pilot_results.docx"
FIG = f"{ROOT}/figures"

NICE = {"clip": "CLIP ViT-B/32", "clip_l14": "CLIP ViT-L/14",
        "clip_l14_squash": "CLIP ViT-L/14 (squash)", "clip_l14_zoom": "CLIP ViT-L/14 (zoom)",
        "biomedclip": "BioMedCLIP ViT-B/16"}
ORDER = ["clip", "clip_l14", "clip_l14_squash", "clip_l14_zoom", "biomedclip"]

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
st.paragraph_format.space_after = Pt(8); st.paragraph_format.line_spacing = 1.15
for lvl, size in ((1, 15), (2, 12.5)):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Calibri"; h.font.size = Pt(size); h.font.bold = True
    h.font.color.rgb = RGBColor(0x1F, 0x3B, 0x63)
    h.paragraph_format.space_before = Pt(14); h.paragraph_format.space_after = Pt(6)


def para(t, bold=False, italic=False, size=None, align=None, after=None):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if align is not None: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p


def table(rows, widths=None, fs=9.5):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.text = ""
            pp = c.paragraphs[0]; pp.paragraph_format.space_after = Pt(2)
            rr = pp.add_run(str(v)); rr.font.size = Pt(fs); rr.bold = (i == 0)
    if widths:
        for j, w in enumerate(widths):
            for i in range(len(rows)):
                t.cell(i, j).width = w
    doc.add_paragraph()
    return t


def figure(name, caption, width=6.4):
    p = f"{FIG}/{name}"
    if not os.path.isfile(p):
        return
    doc.add_picture(p, width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(caption, italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)


# ---------- load results ----------
R = {}
for m in ORDER:
    f = f"{ROOT}/outputs/{m}/results.json"
    if os.path.isfile(f):
        R[m] = json.load(open(f))
OPP = {r["model"]: r for r in json.load(open(f"{ROOT}/outputs/oppositional_analysis.json"))}
GT = json.load(open(f"{ROOT}/data/ground_truth.json"))
QS = {q["id"]: q for q in json.load(open(f"{ROOT}/data/queries.json"))["queries"]}

# ---------- title ----------
para("Fine-Grained Language-Guided Temporal Localisation in a Medical Procedure",
     bold=True, size=17, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Pilot Study: Results", italic=True, size=12.5,
     align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Mehran Piran", size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para(f"{datetime.date.today().strftime('%d %B %Y')}", size=9.5, italic=True,
     align=WD_ALIGN_PARAGRAPH.CENTER, after=14)

# ---------- summary ----------
doc.add_heading("1. What Was Done and What Was Found", level=1)
para(
    "This pilot tested whether a frozen vision-language model can find the moment at which a "
    "specific step of a medical procedure happens, using only a sentence written in normal "
    "language. The video is a single continuous recording of a blood draw that lasts 84 seconds. "
    "No model was trained at any point. Five frozen configurations were compared, and for each of "
    "them three cumulative systems were measured: a frame-by-frame baseline, the same system with "
    "temporal smoothing, and the same system again with the ability to refuse to answer."
)
para("The study produced four findings.", bold=True)
for n, t in enumerate([
    "The size of the vision encoder matters far more than anything else. Moving from CLIP ViT-B/32 "
    "to CLIP ViT-L/14 raised the mean temporal overlap from 0.036 to 0.265, a factor of about seven. "
    "The small model performed at chance and could not be rescued by any later step.",
    "Temporal smoothing produced the single largest improvement of any method step, but only once "
    "the encoder was strong enough to produce a usable signal. With ViT-L/14 it raised the mean "
    "overlap from 0.079 to 0.265, a factor of 3.4. With ViT-B/32 it changed almost nothing.",
    "Allowing the system to refuse to answer cost nothing. The full system rejected every "
    "out-of-video query and a quarter of the hard negatives while leaving the localisation accuracy "
    "of the real actions completely unchanged.",
    "The model cannot tell an action apart from its opposite. This is the central result and it is "
    "described in Section 5.",
], 1):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(7)
    p.add_run(f"Finding {n}.  ").bold = True
    p.add_run(t)

# ---------- design corrections ----------
doc.add_heading("2. Two Corrections to the Original Plan", level=1)
para(
    "Before any model was run, all 84 sampled frames were inspected by eye in order to write the "
    "ground truth. That inspection changed the design of the study in two ways, and both changes "
    "made the benchmark harder and more honest."
)
para(
    "First, the tourniquet is already tied around the patient's arm in the very first frame, and it "
    "is still tied in the very last frame. It is never applied and never removed while the camera is "
    "running. The two queries that describe tying and untying the tourniquet were therefore moved "
    "from the positive set into the hard-negative set. They are unusually demanding negatives, "
    "because the blue tourniquet is clearly visible in every single frame of the video, so the model "
    "must reject an action whose object is permanently on screen."
)
para(
    "Second, the blood is collected into two tubes, not one. The first tube is filled between 45 and "
    "72 seconds, is removed at about 73 seconds, and a second tube is attached and begins to fill at "
    "about 82 seconds. Only the first fill was annotated as the ground truth for the collection "
    "query. The second fill is recorded in the ground-truth file as a known ambiguity and is not "
    "quietly merged into the annotation, because a prediction that lands there is genuinely correct "
    "in appearance while being wrong against the annotation."
)

# ---------- data ----------
doc.add_heading("3. Data and Ground Truth", level=1)
para(
    "The video is a freely licensed clip of a blood examination, 1280 by 720 pixels, 23.976 frames "
    "per second, 84.42 seconds long. One frame was taken every second, giving 84 frames. Thirteen "
    "queries were written by hand: six positive queries describing steps that really happen, four "
    "oppositional hard negatives that reuse the same vocabulary to describe something that never "
    "happens, and three easy negatives describing entirely different procedures. The true start and "
    "end time of each positive action was marked by hand, and the rule used to place each boundary "
    "was written down alongside it."
)
rows = [("Query", "Action", "Ground truth (s)", "Duration")]
for qid in ["p1", "p2", "p3", "p4", "p5", "p6"]:
    g = GT["intervals"][qid]
    rows.append((qid, QS[qid]["name"].replace("_", " "),
                 f"{g['start']} – {g['end']}", f"{g['end']-g['start']+1} s"))
table(rows, [Inches(0.8), Inches(2.3), Inches(1.6), Inches(1.1)])
para("Table 1. The six annotated actions. Together they cover 53 of the 84 seconds.",
     italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)

# ---------- main results ----------
doc.add_heading("4. Main Results", level=1)
para(
    "Table 2 reports the mean temporal intersection over union across the six positive queries, "
    "together with the recall at two overlap levels and the ability to reject queries that describe "
    "actions the video does not contain. E1 scores every frame on its own. E2 adds temporal "
    "smoothing. E3 adds the refusal rule, whose two thresholds were fitted on the three easy "
    "negatives only, so that the hard negatives remain an untouched test."
)
rows = [("Configuration", "E1 mean tIoU", "E2 mean tIoU", "E3 mean tIoU",
         "E2 R@0.3", "E2 R@0.5", "E3 reject hard", "E3 reject easy")]
for m in ORDER:
    if m not in R: continue
    s = R[m]["summary"]
    rows.append((NICE[m],
                 f"{s['E1_baseline']['mean_tIoU']:.3f}",
                 f"{s['E2_temporal']['mean_tIoU']:.3f}",
                 f"{s['E3_abstention']['mean_tIoU']:.3f}",
                 f"{s['E2_temporal']['R@0.3']:.2f}",
                 f"{s['E2_temporal']['R@0.5']:.2f}",
                 f"{s['E3_abstention']['rejection_acc_hard']:.2f}",
                 f"{s['E3_abstention']['rejection_acc_easy']:.2f}"))
table(rows, fs=8.5)
para("Table 2. All five frozen configurations across the three systems. "
     "CLIP ViT-L/14 with temporal smoothing is the best system.",
     italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)

figure("fig4_summary.png",
       "Figure 1. Localisation accuracy and rejection accuracy for every configuration. "
       "Refusing to answer costs nothing in accuracy.")

para(
    "Two of the configurations were included in order to test a specific suspicion about the input "
    "rather than about the model. The standard CLIP image pipeline resizes the shorter side of the "
    "frame to 224 pixels and then takes a square crop from the centre, which on a 1280 by 720 frame "
    "keeps only 56 per cent of the width and throws the left and right thirds away before the model "
    "sees anything. The squash configuration avoids the crop by compressing the whole frame into a "
    "square, and the zoom configuration instead crops tightly around the region where the procedure "
    "takes place. Squashing made the results much worse, falling from 0.265 to 0.085, which suggests "
    "that matching the shape of images the model was trained on matters more than keeping all of the "
    "content. Zooming nearly doubled the accuracy of the frame-by-frame baseline, from 0.079 to "
    "0.151, but finished below the standard pipeline once smoothing was applied. The input pipeline "
    "is therefore a real factor, but it is a smaller one than the size of the encoder."
)
para(
    "BioMedCLIP finished well behind general CLIP ViT-L/14, at 0.098 against 0.265. This comparison "
    "must be read carefully, because BioMedCLIP uses a ViT-B/16 encoder and is therefore a much "
    "smaller model. Against the general model of comparable size, CLIP ViT-B/32, BioMedCLIP is "
    "clearly better, at 0.098 against 0.036. The fair conclusion is that biomedical pretraining does "
    "help at a fixed model size, but that it does not compensate for a smaller encoder, and that the "
    "images BioMedCLIP learned from, which are figures taken from scientific articles, are a poor "
    "match for video frames recorded in a clinic."
)

per = R["clip_l14"]["per_query"]["E2_temporal"]
rows = [("Query", "Action", "Ground truth", "Predicted", "tIoU")]
for qid in ["p1", "p2", "p3", "p4", "p5", "p6"]:
    r = per[qid]
    rows.append((qid, r["name"].replace("_", " "),
                 f"{r['gt'][0]} – {r['gt'][1]} s",
                 f"{r['pred'][0]:.0f} – {r['pred'][1]:.0f} s",
                 f"{r['tIoU']:.3f}"))
table(rows, [Inches(0.7), Inches(1.9), Inches(1.4), Inches(1.4), Inches(0.8)])
para("Table 3. Per-query results for the best system, CLIP ViT-L/14 with temporal smoothing. "
     "Cleaning the arm is localised well; preparing the needle and changing the tube fail entirely.",
     italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)

figure("clip_l14_fig1_positive_curves.png",
       "Figure 2. Smoothed similarity over time for each positive query, with the annotated "
       "interval in green and the predicted interval in orange.")

# ---------- oppositional ----------
doc.add_heading("5. The Central Result: Actions and Their Opposites", level=1)
para(
    "The most informative result of this pilot is not a score but a failure of a very specific kind. "
    "The query that says the nurse pulls the needle out of the arm describes something that never "
    "happens in this video, and the needle is still in the arm in the final frame. Yet its score "
    "curve over time is almost identical to the curve of the query that says the nurse inserts the "
    "needle. For CLIP ViT-L/14 the correlation between the two curves is 0.97 and both reach their "
    "highest value at exactly the same second."
)
para(
    "This is not a general inability to tell queries apart. The same model separates the needle "
    "query from an unrelated query about an MRI scanner almost perfectly, with a correlation of only "
    "0.06. The model therefore knows very well which procedure it is looking at. What it cannot do "
    "is tell the direction of an action when the objects in the sentence stay the same. Table 4 and "
    "Figure 3 show that this holds for every configuration tested."
)
rows = [("Configuration", "r, opposite action", "r, unrelated action",
         "Distance between peaks")]
for m in ORDER:
    if m not in OPP: continue
    o = OPP[m]
    rows.append((NICE[m], f"{o['r_opposite']:.3f}", f"{o['r_unrelated']:.3f}",
                 f"{o['peak_dist_opposite']} s"))
table(rows, [Inches(1.9), Inches(1.5), Inches(1.5), Inches(1.5)])
para('Table 4. "Inserts the needle" against "pulls the needle out", compared with '
     '"inserts the needle" against "lies inside an MRI scanner".',
     italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=12)

figure("fig2b_oppositional_with_reference.png",
       "Figure 3. The opposite query, shown as a red dashed line, follows the true query almost "
       "exactly. The unrelated reference query sits far below and moves independently.")
figure("fig5_oppositional_separation.png",
       "Figure 4. The same comparison across all five configurations. A larger encoder does not "
       "close the gap, and in fact widens it slightly.")

para(
    "One configuration behaves differently and deserves a note. BioMedCLIP gives the lowest "
    "correlation between the opposite queries, 0.77 rather than 0.97, and places their peaks eleven "
    "seconds apart rather than at the same moment. It is the only model tested that separates the "
    "two directions at all. It is also the weakest model at the localisation task itself. Biomedical "
    "pretraining therefore appears to buy some sensitivity to the fine detail of a clinical action "
    "while costing a great deal of general visual quality. This observation comes from a single pair "
    "of queries on a single video and should be treated as something worth testing properly, not as "
    "an established result."
)

# ---------- limitations ----------
doc.add_heading("6. Limitations", level=1)
for t in [
    "The study uses one video and six annotated actions, so every number carries a large uncertainty "
    "and no statistical claim is made. The results indicate the size and direction of effects, "
    "nothing more.",
    "The ground truth was annotated by a single person from frames sampled once per second, so a "
    "boundary can be wrong by about one second. For the shortest action, inserting the needle, which "
    "lasts four seconds, an error of one second changes the overlap substantially.",
    "The thresholds for refusing to answer were fitted on the three easy negatives. This keeps the "
    "hard negatives honest, but three queries is a very small amount of data on which to calibrate.",
    "The margin part of the refusal rule turned out to carry almost no information. Its fitted value "
    "was negative for every configuration, which means the absolute threshold was doing all of the "
    "work. A better confidence measure is needed.",
    "The video is 84 seconds long, which is far too short to say anything about methods designed for "
    "long untrimmed video, including memory mechanisms.",
]:
    p = doc.add_paragraph(t, style="List Bullet"); p.paragraph_format.space_after = Pt(5)

# ---------- next ----------
doc.add_heading("7. What This Suggests Next", level=1)
para(
    "The clearest direction follows from Section 5. A frozen contrastive model matches the objects "
    "named in a sentence and is close to blind to the direction of the action that connects them. "
    "Any method that intends to localise fine-grained steps of a procedure will have to supply that "
    "missing information from somewhere else. Three sources are plausible and each can be tested on "
    "this same small benchmark. The first is motion, because the direction of an action is visible "
    "in the change between frames even when it is invisible in any single frame. The second is "
    "order, because the steps of a procedure follow a fixed sequence and a model that knows the "
    "sequence can rule out an insertion that would have to happen after a removal. The third is "
    "explicit training against oppositional pairs, so that the text encoder is forced to separate "
    "two sentences that differ in one word."
)
para(
    "A second and more practical direction is the confidence measure. Refusing to answer is the "
    "property that would make such a system usable in a clinical setting, and in this pilot it was "
    "obtained for free. However, the rule currently rejects only a quarter of the hard negatives, "
    "and the hard negatives are precisely the cases that matter. A confidence measure built on the "
    "shape of the score curve over time, rather than on its height, is the obvious next thing to try."
)
para(
    "Finally, the method should be moved to a longer and untrimmed recording. The present video is "
    "short enough that every query can be compared against every frame directly. On a procedure "
    "lasting tens of minutes this becomes expensive, and the question of which parts of the video to "
    "keep in memory becomes a real one.",
)

# ---------- repro ----------
doc.add_heading("8. Files", level=1)
para("Everything is in the project repository.", size=10.5)
rows = [("Path", "Contents")]
for a, b in [
    ("data/", "the video, 84 sampled frames, frames.csv, queries.json, ground_truth.json, source.txt"),
    ("scripts/01_encode.py", "encodes frames and queries with a frozen model"),
    ("scripts/02_localise.py", "similarity, smoothing, interval selection, refusal rule"),
    ("scripts/03_evaluate.py", "tIoU, recall, rejection accuracy"),
    ("scripts/04_figures.py", "per-query curves and summary bars"),
    ("scripts/05_oppositional.py", "the oppositional-pair analysis of Section 5"),
    ("scripts/run_all.sh", "reproduces the whole study in one command"),
    ("outputs/<config>/", "embeddings, scores, predictions and results for each configuration"),
    ("figures/", "all figures, plus the frame sheets used to write the ground truth"),
]:
    rows.append((a, b))
table(rows, [Inches(1.9), Inches(4.3)], fs=9)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print("WROTE", OUT, os.path.getsize(OUT), "bytes")

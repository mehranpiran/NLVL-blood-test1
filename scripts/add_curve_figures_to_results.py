#!/usr/bin/env python3
"""
Append the four per-query score-curve figures to Results.docx as Figures 5 to 8,
each with a caption and one paragraph of explanation.

The order follows the order the figures were asked for: BioMedCLIP, CLIP
ViT-L/14, CLIP ViT-L/14 with the zoom crop, then CLIP ViT-B/32.

Nothing already in the document is changed.
"""
import argparse, os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ap = argparse.ArgumentParser()
ap.add_argument("--doc", default="Results.docx")
ap.add_argument("--figdir", default=".")
ap.add_argument("--start", type=int, default=5, help="number of the first figure added")
A = ap.parse_args()

WIDTH = 6.0

INTRO = (
    "The four figures below show the same thing for four of the frozen settings, so that the "
    "numbers in the abstract can be checked query by query. Each figure has one panel for "
    "each of the six real actions. Time in seconds runs along the bottom of every panel and "
    "the smoothed similarity score runs up the side. The dark line is the score curve of that "
    "query. The green band is the true time of the action and the orange band is the time the "
    "system predicted. The number printed in the top right corner of a panel is the time "
    "overlap for that action, where 1 would be a perfect answer and 0 means the two bands do "
    "not touch at all. A good result looks like an orange band sitting on top of a green band."
)

FIGS = [
    ("biomedclip_fig1_positive_curves.png",
     "Score curves for the six real actions, BioMedCLIP ViT-B/16.",
     "BioMedCLIP reaches a mean overlap of 0.098. Only two of the six actions are found at "
     "all. Cleaning the arm scores 0.412, but the predicted band runs from 0 to 16 seconds "
     "while the action lasts from 1 to 7 seconds, so the model has found the right region and "
     "not the right boundaries. Collecting the blood scores 0.179. The other four actions "
     "score zero, and the way they fail is the interesting part. Inserting the needle, "
     "attaching the tube and collecting the blood all peak between 57 and 70 seconds, which is "
     "the long stretch where the tube is filling, while preparing the needle and changing the "
     "tube both peak at 4 seconds. Six different sentences are therefore being answered with "
     "only two places in the video. The model has learned from figures printed in scientific "
     "papers, and those are a poor match for a video recorded in a clinic."),
    ("clip_l14_fig1_positive_curves.png",
     "Score curves for the six real actions, CLIP ViT-L/14. This is the best system in the "
     "study.",
     "This is the setting that reaches a mean overlap of 0.265. Cleaning the arm is found well "
     "at 0.714, and the first panel shows a clean single peak inside the green band. "
     "Collecting the blood scores 0.429 and attaching the tube scores 0.333, but in both cases "
     "the orange band is much shorter than the green one, so the model finds the moment and "
     "underestimates how long the action lasts. Two actions score zero. Preparing the needle "
     "happens from 11 to 15 seconds and the system answers 19 to 43 seconds. Changing the tube "
     "happens from 73 to 77 seconds and the system answers 31 to 41 seconds, which is not even "
     "close. Three of the six curves peak between 32 and 36 seconds, in the middle of the "
     "video where the hands work close to the arm and every frame looks much like the one "
     "before it. The model matches the objects named in the sentence and has little sense of "
     "when the action happens."),
    ("clip_l14_zoom_fig1_positive_curves.png",
     "Score curves for the six real actions, CLIP ViT-L/14 with a tight crop around the "
     "procedure.",
     "This setting crops a fixed box around the place where the procedure happens, instead of "
     "letting the standard pipeline cut a square from the centre of the frame and throw away "
     "the left and right thirds. Cropping helped before smoothing, where it almost doubled the "
     "score, but after smoothing it reaches 0.201 and so finishes below the standard pipeline "
     "at 0.265. The figure shows why. Attaching the tube is the best result of any setting in "
     "the study at 0.400, and cleaning the arm still scores 0.625, so the crop does help when "
     "the action is in the cropped box. Against that, preparing the needle, inserting the "
     "needle and changing the tube now all peak within one second of each other, at 36 or 37 "
     "seconds. Removing the background removed information that was keeping those three "
     "queries apart."),
    ("clip_fig1_positive_curves.png",
     "Score curves for the six real actions, CLIP ViT-B/32. This is the weakest setting.",
     "This is the small model, with a mean overlap of 0.036, and the figure shows a failure "
     "that is different in kind from the others. Four of the six curves peak between 65 and 70 "
     "seconds, and a fifth peaks at 69 seconds, so almost every query is answered with the "
     "same late part of the video no matter what the sentence says. The curves are nearly "
     "copies of each other. What the model is responding to is the frame rather than the "
     "query, which means its output carries almost no information about the sentence that was "
     "asked. Only collecting the blood gets a non-zero overlap, at 0.214, and that happens by "
     "luck, because the true action is long and happens to cover the region the model always "
     "picks. Comparing this figure with Figure 6 is the clearest way to see why the size of "
     "the visual encoder mattered more than anything else that was tested."),
]

doc = Document(A.doc)

p = doc.add_paragraph(style="Normal (Web)")
p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(10)
p.add_run(INTRO).font.size = Pt(11)

for i, (fn, caption, body) in enumerate(FIGS, A.start):
    path = os.path.join(A.figdir, fn)
    if not os.path.isfile(path):
        raise SystemExit(f"missing figure: {path}")

    q = doc.add_paragraph(); q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    q.paragraph_format.space_before = Pt(10); q.paragraph_format.space_after = Pt(4)
    q.add_run().add_picture(path, width=Inches(WIDTH))

    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(6)
    r = cap.add_run(f"Figure {i}. {caption}")
    r.italic = True; r.font.size = Pt(9.5)

    t = doc.add_paragraph(style="Normal (Web)")
    t.paragraph_format.space_after = Pt(14)
    t.add_run(body).font.size = Pt(11)

doc.save(A.doc)
print("UPDATED", A.doc, os.path.getsize(A.doc), "bytes;", len(FIGS), "figures appended")

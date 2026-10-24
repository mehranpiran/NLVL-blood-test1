#!/usr/bin/env python3
"""
Append four figures to Main.docx, one for each claim written in red in the
abstract. Each figure gets a caption and a short paragraph of explanation.

The script only appends. Nothing already in the document is altered.

Mapping from red sentence to figure:
  "strongest model was CLIP ViT-L/14 ... 0.079 to 0.265"   -> Figure 1
  "BioMedCLIP outperformed a general CLIP of similar size" -> Figure 1
  "abstention rejected all easy and one of four hard"      -> Figure 2
  "could not distinguish an action from its opposite"      -> Figure 3
  "correlation of 0.969 and the same peak time"            -> Figure 3, Figure 4
"""
import argparse, os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ap = argparse.ArgumentParser()
ap.add_argument("--doc", default="Main.docx")
ap.add_argument("--figdir", default=".")
A = ap.parse_args()

WIDTH = 6.0  # inches of usable page width in this document

FIGS = [
    ("fig4_summary.png",
     "Localisation accuracy and rejection ability for all five frozen settings.",
     "This figure supports the first two highlighted results. The left panel gives the mean "
     "temporal IoU for the three systems, and the right panel gives the share of absent "
     "actions that were refused. Each colour is one frozen setting. In the left panel the bars "
     "for CLIP ViT-L/14 are far taller than the bars for CLIP ViT-B/32, which is the effect of "
     "the larger visual encoder. Every setting also rises from E1 to E2, which is the effect of "
     "temporal smoothing, and for ViT-L/14 this is the step that raises the score from 0.079 to "
     "0.265. BioMedCLIP sits above CLIP ViT-B/32 but clearly below ViT-L/14, which is the "
     "comparison stated in the abstract. The bars in the right panel are zero for E1 and E2 "
     "because only E3 is allowed to refuse an answer."),
    ("fig6_abstention.png",
     "What the abstention rule catches, and what it costs, for CLIP ViT-L/14.",
     "This figure supports the highlighted result about abstention. The left panel splits the "
     "absent actions into the two kinds used in this study. All three easy negatives, which "
     "describe a different procedure, were correctly refused. Only one of the four hard "
     "negatives was refused, and those four reuse the same objects as a real action, so they "
     "are the cases that matter. The right panel shows the price paid for this ability. The "
     "mean temporal IoU is 0.265 both before and after the rule is switched on, and no real "
     "action was wrongly refused, so for this model the ability to say nothing was obtained at "
     "no cost in accuracy."),
    ("fig2b_oppositional_with_reference.png",
     "A true action, its opposite, and an unrelated action, scored over time by CLIP ViT-L/14.",
     "This figure supports the most important highlighted result. Time in seconds runs along "
     "the bottom and the smoothed similarity score runs up the side. The green band marks the "
     "seconds when the needle is really inserted. The solid dark line is the query describing "
     "needle insertion and the red dashed line is the query describing needle removal, which "
     "never happens anywhere in this video. The two lines rise and fall together, agree with a "
     "correlation of 0.969, and reach their highest value at the same second. The grey dotted "
     "line is an unrelated query about an MRI scanner, and it stays far below and moves on its "
     "own. Together the three lines show that the model recognises the medical context very "
     "well while remaining unable to tell the direction of the action."),
    ("fig5_oppositional_separation.png",
     "Agreement with the opposite action compared with agreement with an unrelated action, "
     "for all five settings.",
     "This figure shows that the previous result is not a property of one model. For each "
     "setting the dark red bar is the correlation between the insertion query and the removal "
     "query, and the light blue bar is the correlation between the insertion query and the "
     "unrelated MRI query. The dark red bars stay high everywhere, between 0.77 and 0.98, while "
     "the light blue bars stay low, between minus 0.15 and 0.27. A larger encoder does not close "
     "this gap and in fact widens it. Only BioMedCLIP, on the right, lowers the dark red bar at "
     "all, and it is also the weakest model at localisation, so this observation is a lead for "
     "future work rather than a solution."),
]

doc = Document(A.doc)

h = doc.add_paragraph(style="Heading 2")
h.add_run("Figures")

for i, (fn, caption, body) in enumerate(FIGS, 1):
    path = os.path.join(A.figdir, fn)
    if not os.path.isfile(path):
        raise SystemExit(f"missing figure: {path}")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(path, width=Inches(WIDTH))

    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(6)
    r = cap.add_run(f"Figure {i}. {caption}")
    r.italic = True; r.font.size = Pt(9.5)

    t = doc.add_paragraph(style="Normal (Web)")
    t.paragraph_format.space_after = Pt(14)
    rr = t.add_run(body); rr.font.size = Pt(11)

doc.save(A.doc)
print("UPDATED", A.doc, os.path.getsize(A.doc), "bytes;", len(FIGS), "figures appended")

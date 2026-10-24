#!/usr/bin/env python3
"""Build the multi-video / time-reversal addendum report."""
import json, os, datetime
import numpy as np
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root
OUT  = f"{ROOT}/docs/NLVL_multivideo_timereversal.docx"
EMB  = f"{ROOT}/corpus/emb/clip_l14"

AOT = json.load(open(f"{EMB}/arrow_of_time.json"))
CAP = json.load(open(f"{EMB}/caption_direction.json"))
FPS = json.load(open(f"{EMB}/fps_check_frames_4fps.json"))
CUR = json.load(open(f"{ROOT}/corpus/manifest/curated.json"))

doc = Document()
st = doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(11)
st.paragraph_format.space_after=Pt(8); st.paragraph_format.line_spacing=1.15
for lvl,size in ((1,15),(2,12.5)):
    h=doc.styles[f"Heading {lvl}"]; h.font.name="Calibri"; h.font.size=Pt(size)
    h.font.bold=True; h.font.color.rgb=RGBColor(0x1F,0x3B,0x63)
    h.paragraph_format.space_before=Pt(14); h.paragraph_format.space_after=Pt(6)

def para(t,bold=False,italic=False,size=None,align=None,after=None):
    p=doc.add_paragraph(); r=p.add_run(t); r.bold=bold; r.italic=italic
    if size: r.font.size=Pt(size)
    if align is not None: p.alignment=align
    if after is not None: p.paragraph_format.space_after=Pt(after)
    return p

def table(rows,widths=None,fs=9.5,cap=None):
    t=doc.add_table(rows=len(rows),cols=len(rows[0]))
    t.style="Light Grid Accent 1"; t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,row in enumerate(rows):
        for j,v in enumerate(row):
            c=t.cell(i,j); c.text=""; pp=c.paragraphs[0]
            pp.paragraph_format.space_after=Pt(2)
            rr=pp.add_run(str(v)); rr.font.size=Pt(fs); rr.bold=(i==0)
    if widths:
        for j,w in enumerate(widths):
            for i in range(len(rows)): t.cell(i,j).width=w
    doc.add_paragraph()
    if cap: para(cap,italic=True,size=9,align=WD_ALIGN_PARAGRAPH.CENTER,after=12)

para("Multiple Videos and the Time-Reversal Test",bold=True,size=17,
     align=WD_ALIGN_PARAGRAPH.CENTER,after=4)
para("An addendum to the NLVL pilot study",italic=True,size=12.5,
     align=WD_ALIGN_PARAGRAPH.CENTER,after=4)
para("Mehran Piran",size=11,align=WD_ALIGN_PARAGRAPH.CENTER,after=2)
para(datetime.date.today().strftime("%d %B %Y"),size=9.5,italic=True,
     align=WD_ALIGN_PARAGRAPH.CENTER,after=14)

doc.add_heading("1. Why the Study Was Extended",level=1)
para(
 "The first pilot rested on a single video. Its most interesting result was that a frozen "
 "vision-language model could not tell an action apart from its opposite: the query describing "
 "the needle being pulled out of the arm followed the query describing the needle going in almost "
 "exactly, with a correlation of 0.97. That observation came from one pair of curves in one "
 "recording, so it could not be separated from an accident of that particular video. The purpose "
 "of this extension was to collect more videos of the same kind and find out whether the result "
 "holds in general.")

doc.add_heading("2. The Corpus",level=1)
inc=CUR["included"]; exc=CUR["excluded"]
shoots=sorted(set(r["shoot"] for r in inc))
para(
 f"Twenty-one clips were collected, all of them close-up recordings of a needle procedure on a "
 f"human arm, and all of them freely licensed. They contain {sum(r['n_frames'] for r in inc)} "
 f"frames sampled once per second and come from {len(shoots)} independent shoots. The shoot "
 "matters because several clips were filmed in one session with the same room, the same patient "
 "and the same camera. Such clips are almost copies of each other, so any evaluation that split "
 "them between training and testing would be measuring memory rather than generalisation. Every "
 "experiment below therefore holds out a whole shoot at a time.")
para(
 f"A further {len(exc)} clips were downloaded and then rejected after their frames were "
 "inspected. Six were rejected for framing, being either wide shots containing two whole people "
 "or a laboratory bench with no arm in view. Earlier, eleven of fourteen candidates from a second "
 "archive had already been rejected because they turned out to be instructional videos with a "
 "presenter and slides, documentary interviews, a clip of only one and a half seconds, or a "
 "static arm in which no action takes place at all. Screening on the actual frames rather than on "
 "the titles was essential, because the titles were frequently misleading.")
rows=[("Shoot","Clips","Example title")]
for s in shoots:
    cl=[r for r in inc if r["shoot"]==s]
    rows.append((s,len(cl),cl[0]["title"][:46]))
table(rows,[Inches(0.9),Inches(0.9),Inches(4.4)],
      cap="Table 1. The curated corpus, grouped by the shoot each clip came from.")

doc.add_heading("3. The Time-Reversal Test",level=1)
para(
 "Playing a clip of a blood draw backwards produces a clip of the opposite procedure. A tourniquet "
 "that was being tied is now being untied, and a needle that was going in is now coming out. The "
 "two versions contain exactly the same pixels in exactly the same lighting, and differ only in "
 "the order of the frames. This gives a perfectly controlled test of whether a model understands "
 "the direction of an action, and the labels come for free.")

doc.add_heading("3.1 A frozen model cannot pass this test, by construction",level=2)
para(
 "Reversing a clip does not change which frames it contains, only their order. Any score computed "
 "by taking the highest or the average similarity over the frames must therefore return an "
 "identical number. The smoothing step used in the pilot does not help either, because a symmetric "
 "three-tap kernel simply mirrors the score curve. The consequence is not that the method happens "
 "to perform badly, but that it is mathematically unable to perform above chance.")
para(
 f"This was checked numerically rather than only argued. Across all {AOT['loso_n']} clips the "
 f"largest difference between the forward score and the reversed score was "
 f"{AOT['invariance_max_diff']:.2e}, which is the precision of the arithmetic. The earlier "
 "correlation of 0.97 is therefore not a curiosity of one video. It is a structural property of "
 "every method that scores frames independently and then combines them symmetrically.",bold=False)
para(
 "This is the strongest result of the extension. It converts an observation into a statement that "
 "holds for any video and any query.",bold=True)

doc.add_heading("3.2 A simple asymmetric remedy does not work",level=2)
para(
 "If the problem is that the operator is symmetric, the obvious repair is to use an asymmetric "
 "one. The displacement between the last and the first frame of a clip changes sign exactly when "
 "the clip is reversed, so a classifier built on it cannot be fooled by appearance alone. Three "
 "versions of this idea were tested and none of them worked.")
rows=[("Test","What it assumes","Result","p")]
rows.append(("Shared direction of progress, "
             "leave-one-shoot-out","All clips advance along one common direction",
             f"{AOT['loso_correct']}/{AOT['loso_n']} = {AOT['loso_acc']:.3f}",
             f"{AOT['binomial_p']:.2f}"))
rows.append(("Caption direction, zero-shot","Each clip has its own pair of opposite captions",
             f"{CAP['correct']}/{CAP['n']} = {CAP['acc']:.3f}", f"{CAP['binomial_p']:.2f}"))
for stat,lab in (("endpoint","Endpoint displacement at 4 fps"),
                 ("step_vote","Fraction of steps along the caption axis, 4 fps"),
                 ("step_mean","Mean per-step projection, 4 fps")):
    k=sum(1 for r in FPS if r[stat]>0)
    rows.append((lab,"Finer sampling exposes the motion",f"{k}/{len(FPS)}","n.s."))
table(rows,[Inches(2.1),Inches(2.1),Inches(1.2),Inches(0.7)],fs=9,
      cap="Table 2. Every attempt to recover the direction of the action. "
          "None is distinguishable from chance.")
para(
 "The first of these tests was poorly designed, and that should be said plainly. It assumes that "
 "every clip moves along a single shared direction, but a clip in which a tourniquet is applied "
 "and a clip in which blood is drawn genuinely travel in different directions, so averaging them "
 "into one vector is the wrong model. The shoots containing the most clips performed worst, which "
 "is exactly what that mistake would produce. The second test avoids the flaw by giving every clip "
 "its own pair of opposite captions, and it still finds nothing.")
m=[abs(r["step_mean"]) for r in FPS]
para(
 "The sizes of the measurements are more informative than the accuracies. At four frames per "
 f"second the mean projection of each frame-to-frame step onto the caption direction was between "
 f"{min(m):.4f} and {max(m):.4f} in absolute value. The movement of the embedding from one frame "
 "to the next is, to a very good approximation, at right angles to the direction in which language "
 "separates an action from its reverse. There is no weak signal being hidden by noise. There is "
 "no signal.")
para(
 "One methodological point is worth recording because it nearly produced a meaningless experiment. "
 "The displacement between the first and last frame is the sum of all the steps in between, so the "
 "average step points in precisely the same direction no matter how finely the video is sampled. "
 "Testing it at a higher frame rate would have changed nothing and the unchanged result could "
 "easily have been read as evidence. The two additional statistics were introduced because they "
 "are non-linear in the trajectory and therefore genuinely depend on the sampling rate.")

doc.add_heading("4. What This Means",level=1)
para(
 "The extension produced one firm positive result and a set of firm negative ones. The positive "
 "result is that the inability of a frozen image-text model to perceive the direction of an action "
 "is provable rather than incidental. The negative results are that the cheapest repairs, which "
 "read a direction out of the existing embeddings, recover nothing at all.")
para(
 "Taken together these point at a single conclusion. The information about which way an action is "
 "going does not appear to be present in the frame embeddings in any form that a linear read-out "
 "can reach. Recovering it will require a model that looks at how the image changes rather than at "
 "what each image contains, which means either optical flow or a video encoder trained on motion. "
 "Adding a read-out to a frame-wise encoder is not enough.")
para(
 "The honest limitation of this conclusion is the size of the corpus. Twenty-one clips across "
 "eleven shoots is enough to prove the first point, which is a mathematical argument confirmed "
 "numerically, but it is not enough to establish a negative result about every possible read-out. "
 "The correct summary is that the simple remedies fail and that the corpus is too small to support "
 "a positive claim even if a more elaborate one would succeed.")

doc.add_heading("5. Files",level=1)
rows=[("Path","Contents")]
for a,b in [("corpus/frames/","21 clips sampled at 1 fps, 460 frames"),
            ("corpus/frames_4fps/","4 clips sampled at 4 fps, 352 frames"),
            ("corpus/manifest/curated.json","the included and excluded clips, with a reason for each exclusion"),
            ("corpus/emb/clip_l14/","frame embeddings and the result file for every test"),
            ("scripts/06_encode_corpus.py","encodes the corpus with a frozen model"),
            ("scripts/07_arrow_of_time.py","the invariance proof and the shared-direction test"),
            ("scripts/08_caption_direction.py","the zero-shot caption-direction test"),
            ("scripts/09_fps_check.py","the order-sensitive statistics at 4 fps")]:
    rows.append((a,b))
table(rows,[Inches(2.2),Inches(4.0)],fs=9)

os.makedirs(os.path.dirname(OUT),exist_ok=True)
doc.save(OUT)
print("WROTE",OUT,os.path.getsize(OUT),"bytes")

p = "scripts/make_nlvl_proposal.py"
s = open(p).read()

old_res = '"about one minute "\n    "and twenty-four seconds and has a resolution of 1080p. It is a single unbroken recording. "'
new_res = '"about one minute "\n    "and twenty-four seconds and has a resolution of 1280 by 720 pixels. It is a single "\n    "unbroken recording. "'
if old_res in s:
    s = s.replace(old_res, new_res); print("resolution: patched")
else:
    import re
    n = s.count("1080p")
    s = s.replace("a resolution of 1080p", "a resolution of 1280 by 720 pixels")
    print(f"resolution: replaced {n} mention(s) of 1080p")

anchor = 'doc.add_heading("1. Summary of the Project", level=1)'
note = '''para(
    "Revision note. This proposal was written before the video was inspected frame by frame. That "
    "inspection changed two things. The tourniquet is already tied in the first frame and is never "
    "applied or removed on camera, so the two tourniquet queries became hard negatives instead of "
    "positive queries. The blood is also collected into two tubes rather than one. Both changes are "
    "recorded in the results report, which supersedes this document where they disagree.",
    italic=True, size=9.5, space_after=12)

'''
if "Revision note." not in s:
    assert anchor in s, "anchor not found"
    s = s.replace(anchor, note + anchor, 1)
    print("revision note: added")
open(p, "w").write(s)
print("done")

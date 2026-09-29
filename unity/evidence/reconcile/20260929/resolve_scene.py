#!/usr/bin/env python3
"""Resolve the single scene conflict by keeping BOTH sides (independent YAML documents),
then verify the merged scene = main + exactly the crafting/devui scene delta."""
import os, re, subprocess, sys
W = os.environ["TMPDIR"] + "/merge"
R = "/home/teknetik/code/ao2"
SCENE = R + "/unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity"
lines = open(W + "/merged.unity", errors="surrogateescape", newline="").read().split("\n")
out, state, ours, theirs = [], 0, [], []
for ln in lines:
    if ln.startswith("<<<<<<< "): state = 1; continue
    if ln.startswith("=======") and state == 1: state = 2; continue
    if ln.startswith(">>>>>>> ") and state == 2:
        # both sides are whole YAML documents: keep main's, then devui's
        out += ours + theirs; ours, theirs, state = [], [], 0; continue
    if state == 1: ours.append(ln)
    elif state == 2: theirs.append(ln)
    else: out.append(ln)
assert state == 0
text = "\n".join(out)
def ids(t): return re.findall(r"^--- !u!(\d+) &(\d+)", t, re.M)
main = open(W + "/main.unity", errors="surrogateescape", newline="").read()
base = open(W + "/base.unity", errors="surrogateescape", newline="").read()
dev = open(W + "/devui.unity", errors="surrogateescape", newline="").read()
im, ib, id_, io = set(ids(main)), set(ids(base)), set(ids(dev)), set(ids(text))
added_dev = id_ - ib
print("docs: main", len(im), "merged", len(io))
print("merged - main == devui additions:", (io - im) == added_dev, sorted(io - im))
print("main - merged (lost):", sorted(im - io))
import collections
cnt = collections.Counter(re.findall(r"^--- !u!\d+ &(\d+)", text, re.M))
dup = [k for k, v in cnt.items() if v > 1]
print("duplicate ids:", dup)
open(W + "/resolved.unity", "w", errors="surrogateescape", newline="").write(text)
if "--apply" in sys.argv:
    open(SCENE, "w", errors="surrogateescape", newline="").write(text)
    print("scene written")

#!/usr/bin/env python3
"""Apply unique crafting + dev-UI work onto main's working tree (t_c7c1e1ca).

Non-scene paths: written from the snapshot commits (devui preferred; crafting-only
evidence added for provenance). Refuses to overwrite an existing main file whose
content differs from HEAD (i.e. anything main has dirtied). Scene: separate 3-way merge.
Reversible: main snapshot = refs/snapshots/t_c7c1e1ca/main.
"""
import os, subprocess, sys
R = "/home/teknetik/code/ao2"
SCENE = "unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity"
D, C = (f"refs/snapshots/t_c7c1e1ca/{n}" for n in ("devui", "crafting"))
APPLY = "--apply" in sys.argv

def git(*a, raw=False):
    r = subprocess.run(["git", "-C", R, *a], capture_output=True, check=True)
    return r.stdout if raw else r.stdout.decode()

def status_map(ref):
    parts = git("diff", "--name-status", "-z", "--no-renames", "HEAD", ref).split("\0")
    out = {}
    i = 0
    while i < len(parts) - 1:
        st, path = parts[i], parts[i + 1]
        out[path] = st
        i += 2
    return out

dev = status_map(D); cra = status_map(C)
print("devui statuses:", sorted(set(dev.values())), "crafting statuses:", sorted(set(cra.values())))
plan = {}
for p, s in cra.items():
    if p != SCENE and s in ("A", "M"): plan[p] = C
for p, s in dev.items():
    if p != SCENE and s in ("A", "M"): plan[p] = D
skipped = [p for p, s in {**cra, **dev}.items() if s not in ("A", "M") and p != SCENE]
print("to write:", len(plan), "skipped non A/M:", skipped)

problems = []
for p, ref in plan.items():
    fp = os.path.join(R, p)
    if os.path.lexists(fp):
        new = git("show", f"{ref}:{p}", raw=True)
        cur = open(fp, "rb").read()
        if cur == new: continue
        h = subprocess.run(["git", "-C", R, "show", f"HEAD:{p}"], capture_output=True)
        if h.returncode != 0 or h.stdout != cur:
            problems.append(p)
print("destination conflicts with main-dirty content:", problems)
if problems: sys.exit("ABORT: resolve manually")
if not APPLY: sys.exit(0)
n = 0
for p, ref in plan.items():
    fp = os.path.join(R, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    data = git("show", f"{ref}:{p}", raw=True)
    if os.path.lexists(fp) and open(fp, "rb").read() == data: continue
    open(fp, "wb").write(data)
    if git("ls-tree", ref, "--", p).split()[0] == "100755": os.chmod(fp, 0o755)
    n += 1
print("wrote", n, "files")

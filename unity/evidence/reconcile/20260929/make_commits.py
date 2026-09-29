#!/usr/bin/env python3
"""Create three reviewable local commits on main via a temporary index (working tree untouched):
 1. crafting  = HEAD + refs/snapshots/.../crafting delta (exact tree of that worktree's changes)
 2. dev-UI    = crafting -> devui snapshot delta (dev bridge, Item Lab, reconciled overlaps, integrated QA evidence)
 3. reconcile = this task's evidence + read-only ReconcileVerify.cs
The dirty main-only work (Basic General / Tool Exchange / sign / render chunks / AGENTS.md / ProjectSettings) is NOT committed.
Scene committed = HEAD + crafting scene delta (== devui scene), so shop-pass scene edits stay uncommitted.
"""
import os, subprocess, sys, tempfile
R = "/home/teknetik/code/ao2"
S = "refs/snapshots/t_c7c1e1ca/"
def git(*a, env=None, inp=None):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(["git", "-C", R, *a], capture_output=True, env=e, input=inp)
    if r.returncode: sys.exit("git %s failed: %s" % (a, r.stderr.decode()))
    return r.stdout.decode().strip()

head = git("rev-parse", "HEAD")
assert head.startswith("0b4496ad"), head
idx = tempfile.mktemp(prefix="cidx.", dir=os.environ["TMPDIR"]); env = {"GIT_INDEX_FILE": idx}

def commit(tree, parent, msg):
    return git("commit-tree", tree, "-p", parent, "-m", msg)

# 1. crafting: tree of the crafting snapshot commit (HEAD + its delta). It contains no main-only work.
t1 = git("rev-parse", S + "crafting^{tree}")
c1 = commit(t1, head, """Add Ward field-fabricator crafting slice (from feature/ward-crafting)

Salvage loot from feral droids, a data-driven recipe/tag model, atomic cap-aware
shop transactions, the field fabricator station and stabilised pistol grip, HUD
crafting panel, EditMode tests and the Crafting data asset/export.

Source: uncommitted work in /home/teknetik/code/ao2-crafting (feature/ward-crafting)
at HEAD 0b4496ad, captured as refs/snapshots/t_c7c1e1ca/crafting (kanban t_c7c1e1ca).
Scene delta is HEAD + the crafting objects only (fabricator, CraftingSession,
checkpoint_fabricator, Ossa line, recoil tuning).""")

# 2. dev-UI: crafting -> devui delta on top of commit 1
t2 = git("rev-parse", S + "devui^{tree}")
# devui tree contains the reconciled crafting files; its evidence tree drops crafting/20260928 evidence (moved). Keep the
# crafting-lane evidence from commit 1 by overlaying it back, so provenance is preserved.
git("read-tree", t2, env=env)
ev = git("ls-tree", "-r", "-z", t1, "--", "unity/evidence/crafting")
for ent in [e for e in ev.split("\0") if e]:
    meta, path = ent.split("\t", 1)
    mode, typ, sha = meta.split()
    git("update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}", env=env)
t2b = git("write-tree", env=env)
c2 = commit(t2b, c1, """Add Ward native developer console, Item Lab and dev bridge (from feature/ward-dev-ui)

Development-only opt-in dev.* bridge (DevBridgeCommands, correlated ACKs, dev-state.json),
local Python developer console + Item Lab under unity/tools/devui, ShopModel/GameSession
dev adjustments, reconciled with the crafting slice, plus integrated QA evidence.

Source: uncommitted work in /home/teknetik/code/ao2-devui (feature/ward-dev-ui) at HEAD
0b4496ad, captured as refs/snapshots/t_c7c1e1ca/devui (kanban t_c7c1e1ca). Crafting-lane
evidence from commit 1 is retained alongside the dev-UI evidence.""")

# 3. reconcile evidence + verifier
git("read-tree", t2b, env=env)
git("add", "-A", "--", "unity/evidence/reconcile", "unity/AthenHill/Assets/AthenHill/Editor/ReconcileVerify.cs",
    "unity/AthenHill/Assets/AthenHill/Editor/ReconcileVerify.cs.meta", env=env)
t3 = git("write-tree", env=env)
c3 = commit(t3, c2, """Record crafting + dev-UI reconciliation onto main (t_c7c1e1ca)

Snapshots, overlap analysis, scene 3-way merge scripts, EditMode 82/82, development and
release Linux builds, real-input crafting/city/Basic General/Tool Exchange routes,
release bridge denial and read-only scene reopen/chunk-fingerprint check.""")
os.remove(idx)
print(c1, c2, c3, sep="\n")
open(os.environ["TMPDIR"] + "/commits", "w").write("\n".join([c1, c2, c3]))

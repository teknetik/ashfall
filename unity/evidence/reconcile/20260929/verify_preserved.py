#!/usr/bin/env python3
"""Compare main working tree now vs pre-integration snapshot: only expected paths may differ."""
import os, subprocess, tempfile
R = "/home/teknetik/code/ao2"
S = "refs/snapshots/t_c7c1e1ca/"
def git(*a, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(["git", "-C", R, *a], capture_output=True, check=True, env=e).stdout.decode()
idx = tempfile.mktemp(prefix="vidx.", dir=os.environ["TMPDIR"])
env = {"GIT_INDEX_FILE": idx}
git("read-tree", "HEAD", env=env); git("add", "-A", ".", env=env)
now = git("write-tree", env=env).strip(); os.remove(idx)
snap = git("rev-parse", S + "main^{tree}").strip()
changed = [p for p in git("diff", "--name-only", "-z", "--no-renames", snap, now).split("\0") if p]
exp = set(p for r in ("devui", "crafting") for p in git("diff", "--name-only", "-z", "--no-renames", "HEAD", S + r).split("\0") if p)
print("main tree now:", now)
print("changed vs main snapshot:", len(changed), "| unexpected (not crafting/devui paths):", sorted(set(changed) - exp))
print("expected but unchanged:", len(exp - set(changed)))
open(os.environ["TMPDIR"] + "/now_tree", "w").write(now)

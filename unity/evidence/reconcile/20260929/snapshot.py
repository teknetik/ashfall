#!/usr/bin/env python3
"""Non-destructive snapshot of the three dirty Ward trees (task t_c7c1e1ca).

For each tree: build a commit (parent = HEAD) from a *temporary* index that
contains the full working tree (tracked changes, deletions and untracked,
non-ignored files), and record it under refs/snapshots/t_c7c1e1ca/<name>.
The real index, working tree and branches are not touched. Also writes a
tarball of dirty/untracked files and the porcelain status.
"""
import os, subprocess, sys, tempfile, tarfile

ROOT = "/home/teknetik/code"
OUT = f"{ROOT}/_snapshots_20260929"
TREES = {"main": "ao2", "crafting": "ao2-crafting", "devui": "ao2-devui"}
ENV_ID = dict(GIT_AUTHOR_NAME="snapshot", GIT_AUTHOR_EMAIL="snap@local",
              GIT_COMMITTER_NAME="snapshot", GIT_COMMITTER_EMAIL="snap@local")

def git(d, *a, env=None, inp=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(["git", "-C", d, *a], env=e, check=True,
                          capture_output=True, text=True, input=inp).stdout.strip()

for name, d in TREES.items():
    path = f"{ROOT}/{d}"
    idx = tempfile.mktemp(prefix="snapidx.", dir=os.environ.get("TMPDIR", "/tmp"))
    env = {"GIT_INDEX_FILE": idx}
    git(path, "read-tree", "HEAD", env=env)
    git(path, "add", "-A", ".", env=env)
    tree = git(path, "write-tree", env=env)
    commit = git(path, "commit-tree", tree, "-p", "HEAD", "-m",
                 f"snapshot of {d} dirty tree before t_c7c1e1ca (2026-09-29)", env={**ENV_ID})
    git(path, "update-ref", f"refs/snapshots/t_c7c1e1ca/{name}", commit)
    os.remove(idx)
    with open(f"{OUT}/{name}-status.txt", "w") as f:
        f.write(git(path, "status", "--porcelain"))
    files = subprocess.run(["git", "-C", path, "ls-files", "-m", "-o", "--exclude-standard", "-z"],
                           capture_output=True, check=True).stdout.split(b"\0")
    n = 0
    with tarfile.open(f"{OUT}/{name}-dirty-files.tgz", "w:gz") as tf:
        for fn in files:
            if not fn: continue
            p = os.path.join(path, fn.decode())
            if os.path.lexists(p):
                tf.add(p, arcname=f"{d}/{fn.decode()}", recursive=False); n += 1
    print(name, d, "tree", tree, "commit", commit, "files-tarred", n)

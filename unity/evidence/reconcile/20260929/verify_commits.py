#!/usr/bin/env python3
"""Check the three new commits against the live working tree: every path in the commits' delta must be byte-identical on disk
(except the scene, which on disk also carries main's shop edits)."""
import os, subprocess, tempfile
R = "/home/teknetik/code/ao2"
SCENE = "unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity"
c1, c2, c3 = open(os.environ["TMPDIR"] + "/commits").read().split()
def git(*a, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(["git", "-C", R, *a], capture_output=True, check=True, env=e).stdout.decode()
idx = tempfile.mktemp(prefix="vidx.", dir=os.environ["TMPDIR"]); env = {"GIT_INDEX_FILE": idx}
git("read-tree", "HEAD", env=env); git("add", "-A", ".", env=env)
work = git("write-tree", env=env).strip(); os.remove(idx)
delta = [p for p in git("diff", "--name-only", "-z", "--no-renames", "HEAD", c3).split("\0") if p]
diff = set(p for p in git("diff", "--name-only", "-z", "--no-renames", work, c3).split("\0") if p)
bad = [p for p in delta if p in diff]
print("commit delta paths:", len(delta), "| differ from working tree:", bad)
snap_main = "refs/snapshots/t_c7c1e1ca/main"
print("working tree vs pre-integration main snapshot changed paths:", len([p for p in git("diff", "--name-only", "-z", "--no-renames", snap_main + "^{tree}", work).split("\0") if p]))
# what remains uncommitted (working tree minus C3)
rest = [p for p in git("diff", "--name-only", "-z", "--no-renames", c3, work).split("\0") if p]
print("uncommitted remainder vs C3:", len(rest))
main_only_expected = set(p for p in git("diff", "--name-only", "-z", "--no-renames", "HEAD", snap_main).split("\0") if p)
print("remainder not in main's original dirty set (unexpected):", sorted(set(rest) - main_only_expected))
print("main dirty paths absent from remainder (would mean committed by accident):", len(main_only_expected - set(rest) - {SCENE}))

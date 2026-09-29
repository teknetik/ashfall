#!/usr/bin/env python3
import subprocess, os
R = "/home/teknetik/code/ao2"
def g(*a):
    return subprocess.run(["git", "-C", R, *a], check=True, capture_output=True, text=True).stdout
def changed(ref):
    # paths that differ between HEAD and snapshot commit
    return set(x for x in g("diff", "--name-only", "-z", "HEAD", ref).split("\0") if x)
m = changed("refs/snapshots/t_c7c1e1ca/main")
c = changed("refs/snapshots/t_c7c1e1ca/crafting")
d = changed("refs/snapshots/t_c7c1e1ca/devui")
print("main", len(m), "crafting", len(c), "devui", len(d))
print("crafting - devui:", sorted(c - d))
print("crafting & devui:", len(c & d), "devui only:", len(d - c))
print("--- overlap main & devui:")
for p in sorted(m & d): print("  ", p)
print("--- overlap main & crafting:")
for p in sorted(m & c): print("  ", p)
# crafting paths whose content differs from devui
diff = set(x for x in g("diff", "--name-only", "-z", "refs/snapshots/t_c7c1e1ca/crafting", "refs/snapshots/t_c7c1e1ca/devui").split("\0") if x)
print("--- devui vs crafting content-different among shared paths:")
for p in sorted(diff & c): print("  ", p)

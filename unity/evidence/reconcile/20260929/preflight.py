#!/usr/bin/env python3
"""Pre-flight checks before applying crafting + dev-UI onto main (read-only)."""
import re, subprocess, json, os, collections
R = "/home/teknetik/code/ao2"
def g(*a, raw=False):
    r = subprocess.run(["git", "-C", R, *a], check=True, capture_output=True)
    return r.stdout if raw else r.stdout.decode("utf-8", "replace")
D, C = "refs/snapshots/t_c7c1e1ca/devui", "refs/snapshots/t_c7c1e1ca/crafting"
def changed(ref):
    return [x for x in g("diff", "--name-only", "-z", "HEAD", ref).split("\0") if x]
newmeta = [p for p in set(changed(D)) | set(changed(C)) if p.endswith(".meta")]
print("new/changed .meta files:", len(newmeta))
guid_re = re.compile(r"^guid: ([0-9a-f]{32})", re.M)
incoming = {}
for p in newmeta:
    try: t = g("show", f"{D}:{p}")
    except subprocess.CalledProcessError:
        try: t = g("show", f"{C}:{p}")
        except subprocess.CalledProcessError: continue
    m = guid_re.search(t)
    if m: incoming[m.group(1)] = p
# existing GUIDs across the main working tree Assets (all .meta)
existing = collections.defaultdict(list)
root = f"{R}/unity/AthenHill/Assets"
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.endswith(".meta"):
            p = os.path.join(dp, f)
            with open(p, errors="replace") as fh:
                m = guid_re.search(fh.read(2000))
            if m: existing[m.group(1)].append(p)
clash = {g_: (incoming[g_], existing[g_]) for g_ in incoming if g_ in existing and not any(e.endswith(incoming[g_]) for e in existing[g_])}
print("incoming GUIDs", len(incoming), "clashes with different path in main:", len(clash))
for k, v in clash.items(): print("  ", k, v)
# scene fileID collisions
scene = open(os.environ["TMPDIR"] + "/merge/main.unity", errors="replace").read()
main_ids = set(re.findall(r"^--- !u!\d+ &(\d+)", scene, re.M))
dev = open(os.environ["TMPDIR"] + "/merge/devui.unity", errors="replace").read()
base = open(os.environ["TMPDIR"] + "/merge/base.unity", errors="replace").read()
dev_ids = set(re.findall(r"^--- !u!\d+ &(\d+)", dev, re.M)); base_ids = set(re.findall(r"^--- !u!\d+ &(\d+)", base, re.M))
added = dev_ids - base_ids; removed = base_ids - dev_ids
print("devui scene adds ids:", sorted(added), "removes:", sorted(removed))
print("added ids colliding with main:", sorted(added & main_ids))
print("base ids missing from main (main removed/renamed):", len(base_ids - main_ids), "main new ids:", len(main_ids - base_ids))
# do the things devui's new objects reference still exist in main?
refs = set(re.findall(r"fileID: (\d+)", "\n".join(re.findall(r"(?s)--- !u!\d+ &(?:118776012|118776013|118776014|118776015|1027828637|1027828638|1233573787|1233573788|1607540213)\n.*?(?=^--- |\Z)", dev, re.M))))
print("referenced ids:", sorted(refs))
print("  not in main:", sorted(r for r in refs if r not in main_ids and r != "0" and r not in added))

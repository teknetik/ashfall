#!/usr/bin/env python3
"""Compile the game's C# without launching Unity.

Unity (Bee) leaves one compiler response file per assembly in Library/Bee/artifacts/*.dag/. This replays them with the
Roslyn compiler that ships with the Editor, after refreshing each source list from disk (new .cs files are picked up,
deleted ones dropped), and writes the outputs to a scratch folder, so nothing in Library/ is touched.

  python3 unity/tools/compile_check.py            # Runtime, then Editor scripts, then Edit Mode tests
  python3 unity/tools/compile_check.py runtime    # just AthenHill.Runtime

It needs about 1 GB of RAM for a few seconds, so it is safe when Unity itself cannot run. It is a compile check only:
it does not import assets, run tests or prove that serialized data still loads. Exit code 0 means no compiler errors.
The response files come from the last Unity run; if packages or asmdefs change, run Unity once to refresh them.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

PROJECT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "AthenHill"))
EDITOR = os.path.expanduser("~/Unity/Hub/Editor/6000.6.0f1/Editor/Data")
DOTNET = os.path.join(EDITOR, "NetCoreRuntime", "dotnet")
CSC = glob.glob(os.path.join(EDITOR, "DotNetSdk", "sdk", "*", "Roslyn", "bincore", "csc.dll"))

# name -> (response file stem, earlier assemblies whose fresh output this one should reference)
ASSEMBLIES = [
    ("runtime", "AthenHill.Runtime", []),
    ("editor", "Assembly-CSharp-Editor", ["AthenHill.Runtime"]),
    ("tests", "AthenHill.EditModeTests", ["AthenHill.Runtime"]),
]


def find_rsp(stem):
    hits = [p for p in glob.glob(os.path.join(PROJECT, "Library", "Bee", "artifacts", "*.dag", stem + ".rsp"))]
    if not hits:
        sys.exit("no response file for %s: run Unity once on this project so Library/Bee exists" % stem)
    return max(hits, key=os.path.getmtime)


def unquote(s):
    return s[1:-1] if len(s) > 1 and s[0] == '"' and s[-1] == '"' else s


def refreshed_sources(old):
    """Sources now on disk in the folders the assembly was built from (so new files count and deleted ones do not)."""
    roots = set()
    for src in old:
        d = os.path.dirname(src)
        # Runtime and test assemblies own a whole asmdef folder; Editor scripts sit in several Editor folders.
        roots.add(d)
    out = set()
    for d in roots:
        full = os.path.join(PROJECT, d)
        if os.path.isdir(full):
            for f in os.listdir(full):
                if f.endswith(".cs"):
                    out.add(os.path.join(d, f))
    # New subfolders of an asmdef root (for example Scripts/NewFeature/) are found by walking up to the asmdef.
    for d in list(roots):
        cur = d
        while cur and cur != "Assets":
            if glob.glob(os.path.join(PROJECT, cur, "*.asmdef")):
                for base, _dirs, files in os.walk(os.path.join(PROJECT, cur)):
                    rel = os.path.relpath(base, PROJECT)
                    if glob.glob(os.path.join(base, "*.asmdef")) and rel != cur:
                        _dirs[:] = []
                        continue
                    # An Editor folder inside a runtime asmdef would belong to it too; this project has none.
                    for f in files:
                        if f.endswith(".cs"):
                            out.add(os.path.join(rel, f))
                break
            cur = os.path.dirname(cur)
    return sorted(out)


def build(name, stem, deps, outdir, fresh):
    rsp = find_rsp(stem)
    lines = [l.rstrip("\n") for l in open(rsp, encoding="utf-8")]
    sources, rest = [], []
    for l in lines:
        u = unquote(l)
        if u.endswith(".cs") and not l.startswith(("-", "/")):
            sources.append(u)
        else:
            rest.append(l)
    new_sources = refreshed_sources(sources)
    added = sorted(set(new_sources) - set(sources))
    removed = sorted(set(sources) - set(new_sources))
    out_dll = os.path.join(outdir, stem + ".dll")
    args = []
    for l in rest:
        if l.startswith("-out:"):
            l = '-out:"%s"' % out_dll
        elif l.startswith("-refout:"):
            l = '-refout:"%s"' % os.path.join(outdir, stem + ".ref.dll")
        elif l.startswith(("-analyzer:", "/additionalfile:")):
            continue  # source generators are not needed for a compile check and slow it down
        elif l.startswith(("-r:", "-reference:")):
            ref = unquote(l.split(":", 1)[1])
            base = os.path.basename(ref)
            for dep in deps:
                if base in (dep + ".dll", dep + ".ref.dll") and dep in fresh:
                    l = '-r:"%s"' % fresh[dep]
        args.append(l)
    args += ['"%s"' % s for s in new_sources]
    new_rsp = os.path.join(outdir, stem + ".rsp")
    with open(new_rsp, "w", encoding="utf-8") as f:
        f.write("\n".join(args) + "\n")
    proc = subprocess.run([DOTNET, CSC[0], "@" + new_rsp], cwd=PROJECT, capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    errors = [l for l in text.splitlines() if re.search(r"\berror\b", l)]
    print("%-8s %-26s %d sources (+%d new, -%d gone)  %s" % (
        name, stem, len(new_sources), len(added), len(removed), "OK" if proc.returncode == 0 else "FAILED"))
    for l in added:
        print("   new: " + l)
    for l in errors[:60]:
        print("   " + l)
    if len(errors) > 60:
        print("   ... %d more errors" % (len(errors) - 60))
    if proc.returncode == 0:
        fresh[stem] = out_dll
    return proc.returncode == 0


def main():
    if not CSC or not os.path.exists(DOTNET):
        sys.exit("Unity's bundled dotnet/Roslyn was not found under " + EDITOR)
    want = [a.lower() for a in sys.argv[1:]] or [a[0] for a in ASSEMBLIES]
    ok = True
    fresh = {}
    with tempfile.TemporaryDirectory(prefix="athen-compile-") as outdir:
        for name, stem, deps in ASSEMBLIES:
            needed = name in want or any(name == "runtime" and w in ("editor", "tests") for w in want)
            if not needed:
                continue
            if not build(name, stem, deps, outdir, fresh):
                ok = False
                if name == "runtime":
                    print("runtime failed; Editor scripts and tests were not compiled")
                    break
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

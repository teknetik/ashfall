#!/usr/bin/env python3
"""Pre-flight C# compile check for this pass's scripts, outside Unity (a compile error in Assets/ would break every
other agent's Unity batch run). Uses Unity's bundled Roslyn csc against the csproj HintPaths and the current
Library/ScriptAssemblies. Usage: python check_compile.py runtime <file.cs ...> | editor <file.cs ...> [--with-runtime f.cs]
Output dlls go to the session scratch dir (argument --out, default ./.check)."""
import re, subprocess, sys, os
from pathlib import Path

U = Path("/home/teknetik/code/ao2/unity/AthenHill")
CSC = "/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/sdk/8.0.318/Roslyn/bincore/csc.dll"
DOTNET = "/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/dotnet"
if not os.path.exists(DOTNET):
    DOTNET = "dotnet"

def refs(csproj):
    t = (U / csproj).read_text()
    hp = re.findall(r"<HintPath>([^<]+)</HintPath>", t)
    defs = re.search(r"<DefineConstants>([^<]+)</DefineConstants>", t).group(1)
    return [h for h in hp if os.path.exists(h)], defs

def compile_(kind, files, extra_refs, out):
    csproj = "AthenHill.Runtime.csproj" if kind == "runtime" else "Assembly-CSharp-Editor.csproj"
    hp, defs = refs(csproj)
    sa = U / "Library/ScriptAssemblies"
    own = [str(d) for d in sorted(sa.glob("*.dll")) if kind == "editor" or "Editor" not in d.name]
    own += [str(d) for d in (U / "Library/PackageCache").glob("com.unity.nuget.newtonsoft-json@*/Runtime/Newtonsoft.Json.dll")]
    names = {Path(h).name for h in hp}
    allrefs = [h for h in hp] + [o for o in own if Path(o).name not in names] + extra_refs
    args = [DOTNET, CSC, "-nologo", "-target:library", "-nostdlib-", "-langversion:9.0", "-warn:0",
            f"-define:{defs}", f"-out:{out}"] + [f"-r:{r}" for r in allrefs] + [str(f) for f in files]
    p = subprocess.run(args, capture_output=True, text=True)
    errs = [l for l in (p.stdout + p.stderr).splitlines() if "error" in l]
    print("\n".join(errs[:40]) if errs else f"{kind}: OK -> {out}")
    return p.returncode

if __name__ == "__main__":
    kind = sys.argv[1]
    outdir = Path(os.environ.get("CHECK_OUT", "/tmp/claude-1000/nightlife-check")); outdir.mkdir(parents=True, exist_ok=True)
    rest = sys.argv[2:]
    extra = []
    if "--with-runtime" in rest:
        i = rest.index("--with-runtime"); rt = rest[i + 1:]; rest = rest[:i]
        dll = outdir / "NightLifeRuntimeCheck.dll"
        if compile_("runtime", rt, [], dll) != 0: sys.exit(1)
        extra = [str(dll)]
    sys.exit(compile_(kind, rest, extra, outdir / f"NightLife{kind}Check.dll"))

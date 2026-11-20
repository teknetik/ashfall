#!/usr/bin/env python3
"""Crafting rework phase 1 (20 Nov 2026): ElevenLabs takes for Ossa's servo identification and Brann's "show it to Ossa".

Reuses art/showcase_20261119/npc_life/generate_voices.py (same model, voice settings, request records, mastering, key from
the project .env, never printed). Lines are in lines.json; voices come from that tool's barks.json speaker list.
Writes the canonical Audio/ElevenLabs/NpcVoices/<npc>-<node>.wav plus a .meta with a deterministic GUID (md5 of the file
name) so the dialogue assets can reference the clip before Unity imports it. Re-runnable: cached takes are not paid for.

  python3 art/crafting_assembly_20261120/generate_voices.py             # dry run
  python3 art/crafting_assembly_20261120/generate_voices.py --generate
"""
import argparse, hashlib, importlib.util, json, sys, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("npc_life", HERE.parent / "showcase_20261119/npc_life/generate_voices.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)

META = """fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 8
  defaultSettings:
    serializedVersion: 2
    loadType: 0
    sampleRateSetting: 0
    sampleRateOverride: 44100
    compressionFormat: 1
    quality: 0.85
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 1
  normalize: 0
  loadInBackground: 0
  ambisonic: 0
  3D: 1
  userData:
  assetBundleName:
  assetBundleVariant:
"""

def guid_for(name):
    return hashlib.md5(("ward-crafting-assembly-20261120/" + name).encode()).hexdigest()

def jobs():
    voices = {s["id"]: s["voice"] for s in base.DATA["speakers"]}
    out = []
    for d in json.loads((HERE / "lines.json").read_text())["dialogue"]:
        name = f"{d['npc']}-{d['node']}"
        out.append(dict(kind="dialogue", priority="a", speaker=d["npc"], line=d["node"], text=d["text"], voice=voices[d["npc"]],
                        mp3=base.STAGE_DIALOGUE / f"{name}.mp3", record=base.STAGE_DIALOGUE / f"{name}.json",
                        wav=base.ASSETS / "NpcVoices" / f"{name}.wav"))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--generate", action="store_true"); args = ap.parse_args()
    key = base.credential() if args.generate else None
    ok = True
    for job in jobs():
        state = base.cached(job)
        if state is None:
            print("stale take, not touched:", job["mp3"].name); ok = False; continue
        if not state and args.generate:
            try:
                base.request(job, key); state = True
            except urllib.error.HTTPError as exc:
                print(f"REFUSED {job['mp3'].name}: HTTP {exc.code} {exc.read().decode(errors='replace')[:200].replace(key, '[REDACTED]')}"); ok = False
            except Exception as exc:
                print(f"FAILED {job['mp3'].name}: {str(exc).replace(key, '[REDACTED]')[:200]}"); ok = False
        if state:
            base.master(job) if not job["wav"].exists() else None
            meta = Path(str(job["wav"]) + ".meta")
            if not meta.exists():
                meta.write_text(META.format(guid=guid_for(job["wav"].name)))
        print(("ok   " if state else "----"), job["speaker"], job["line"], len(job["text"]), "chars")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

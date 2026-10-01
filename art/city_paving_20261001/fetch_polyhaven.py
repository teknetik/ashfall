#!/usr/bin/env python3
"""Fetch the CC0 Poly Haven sources for the city paving pass (1 Oct 2026).

floor_tiles_04 (Rob Tuytel, CC0, 4 x 4 m real size): dressed stone flags, analysed as a size/course reference only
(analyse_source.py); not shipped. worn_rock_natural_01 (CC0, the Ward masonry kit's ashlar source): the flag surfaces
of author_paving.py (albedo + height) and the high-passed close-range grain normal.
Files go to polyhaven/<id>/ (git-ignored), polyhaven/manifest.json records names, authors, licence and URLs."""
import hashlib, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
WANT = {
    "floor_tiles_04": ("4k", ["Diffuse", "nor_gl", "Displacement", "Rough", "AO"]),
    "worn_rock_natural_01": ("2k", ["Diffuse", "nor_gl", "Displacement"]),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AthenHill-asset-fetch/1.0 (local game production)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    manifest = {}
    for aid, (res, maps) in WANT.items():
        files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
        info = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
        got = {}
        for m in maps:
            entry = files[m][res].get("png") or files[m][res].get("jpg")
            dest = ROOT / aid / Path(entry["url"]).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not (dest.exists() and hashlib.md5(dest.read_bytes()).hexdigest() == entry.get("md5")):
                dest.write_bytes(get(entry["url"]))
            got[m] = dest.name
        manifest[aid] = {"name": info["name"], "authors": info["authors"], "license": "CC0 1.0",
                         "source": f"https://polyhaven.com/a/{aid}", "dimensions_mm": info.get("dimensions"),
                         "resolution": res, "files": got}
        print(aid, got)
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()

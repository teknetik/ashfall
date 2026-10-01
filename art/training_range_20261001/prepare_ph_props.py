"""Warden training range: CC0 Poly Haven props for Unity (Blender 5.2 headless, 1 Oct 2026).

Reuses art/street_dressing_20260930/prepare_ph_props.py (join, normalise to the ground with the front to Unity +Z,
collapse-decimated LOD1/LOD2, glTF without images, material -> source map records) with this pass's own sources
(polyhaven/models, fetched by fetch_polyhaven.py) and output folder.

Run:  $O/blender.sh prepare_ph_props.py [-- id ...]
Out:  unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Props/<id>/<id>_LOD0..2.glb and Props/tr-props.json.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/street_dressing_20260930"))
import prepare_ph_props as SDP  # noqa: E402

SDP.PH = HERE / "polyhaven/models"
SDP.OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Props"
SDP.PROPS = {
    "bench_vice": ("bench_vice_01", None, 0, "bench vice, bolted to the repair bench"),
    "megaphone": ("Megaphone_01", None, 0, "range officer's megaphone"),
    "multimeter": ("retro_multimeter", None, 0, "test meter on the repair bench"),
    "compressor": ("old_military_compressor", None, 0, "wheeled air compressor for the drone rotors"),
    "welding_cart": ("portable_welding_cart", None, 0, "welding cart with bottles"),
    "work_lamp": ("caged_hanging_light", None, 0, "caged work lamp hung under the service shelter"),
    "spade": ("rusted_spade_01", None, 0, "spade for berm repairs"),
    "sledgehammer": ("sledgehammer_01", None, 0, "sledgehammer for post repairs"),
}


def main():
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    path = SDP.OUT / "tr-props.json"
    report = json.loads(path.read_text()) if path.exists() else {}
    for pid in SDP.PROPS:
        if only and pid not in only:
            continue
        SDP.prep(pid, report)
    SDP.OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()

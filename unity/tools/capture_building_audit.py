"""Capture every placed primary building from the saved diagnostic cameras.

Run only against an explicitly launched native development player. Does not
launch, quit, build, change resolution, hide the HUD, or change materials. Each
output directory is new so dated comparisons cannot silently overwrite evidence.
Pillow contact sheets summarize captures; native originals remain unchanged.
"""
import argparse
import asyncio
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import time
import uuid

from PIL import Image, ImageDraw, ImageFont
from native_client import Client


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contact_sheets(out, manifest, records):
    lookup = {r["camera"]: r for r in records}
    sections = []
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    for building in manifest["buildings"]:
        canvas = Image.new("RGB", (1920, 900), "#161616")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), building["name"] + " — captured evidence; visual review pending", font=font, fill="white")
        cards = []
        for index, view in enumerate(building["views"]):
            x, y = (index % 3) * 640, 50 + (index // 3) * 420
            record = lookup.get(view["name"])
            path = out / (record["image"] if record else "missing.png")
            if path.exists():
                with Image.open(path) as original:
                    thumbnail = original.convert("RGB")
                    thumbnail.thumbnail((640, 360), Image.Resampling.LANCZOS)
                    canvas.paste(thumbnail, (x, y))
                caption = "CAPTURED / UNREVIEWED"
            else:
                draw.rectangle((x + 2, y, x + 638, y + 358), outline="#666666")
                draw.text((x + 16, y + 160), "MISSING — no visual coverage", font=font, fill="#f1bc65")
                caption = "NOT CAPTURED"
            draw.text((x + 12, y + 365), view["kind"] + " · " + caption, font=font, fill="white")
            draw.text((x + 12, y + 391), "position " + str([round(n, 3) for n in view["position"]]) + " · FOV " + str(view["fov"]), font=small, fill="#bbbbbb")
            img = html.escape(path.name)
            cards.append(f'<figure><a href="{img}"><img src="{img}" alt="{html.escape(view["kind"])}"></a><figcaption>{html.escape(view["kind"])} — {caption}</figcaption><pre>{html.escape(json.dumps(view, indent=2))}</pre></figure>')
        sheet = "contact-" + building["id"] + ".jpg"
        canvas.save(out / sheet, quality=94)
        sections.append(f'<section><h2>{html.escape(building["name"])}</h2><p>{html.escape(building["primaryPath"])}</p><a href="{sheet}">Contact sheet</a><div class="cards">{"".join(cards)}</div></section>')
    (out / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>Ward building audit evidence</title><style>body{background:#161616;color:#eee;font:16px sans-serif;margin:28px}a{color:#b5ddff}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}img{width:100%}pre{max-height:12em;overflow:auto;font-size:12px}section{margin:36px 0}</style><h1>Placed building evidence — visual review pending</h1><p>Native 1920×1080 originals are linked. A captured frame does not establish full coverage, quality, source review or acceptance. Camera overlap/raycast diagnostics are in the manifest. Side views are pedestrian obliques; occluded regions require additional views. No wireframe, movement or performance qualification is produced here.</p><p><a href="saved-camera-manifest.json">Exact saved camera poses and source identities</a> · <a href="capture-report.json">Native capture report</a> · <a href="review-ledger.json">Per-view review ledger</a></p>' + "".join(sections))


async def capture(args):
    manifest = read(args.manifest)
    assert manifest["schema"] == 1 and manifest["sceneDirty"] is False, "A saved-scene manifest is required"
    assert len(manifest["buildings"]) == 10, "Expected all ten primary building placements"
    native = Path(os.environ["ATHEN_NATIVE_DIR"])
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(args.manifest, out / "saved-camera-manifest.json")
    shutil.copyfile(args.build_record, out / "build-record.json")
    report = {"complete": False, "manifestSha256": digest(args.manifest), "buildRecordSha256": digest(args.build_record),
              "buildRecord": read(args.build_record), "buildSceneAssociation": "Provided build record; camera positions are checked in the running player.",
              "views": [], "visualAcceptance": "pending", "performanceQualification": "not measured by this capture tool",
              "startedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    c, restore_clock, previous_error = Client(), None, None
    error_path = native / "qa-error.json"
    if error_path.exists():
        previous_error = digest(error_path)

    async def command(value):
        try:
            await c.command(value)
        except Exception:
            if error_path.exists() and digest(error_path) != previous_error:
                raise RuntimeError("Native QA failure: " + error_path.read_text())
            raise

    async def clock_state():
        await command({"action": "timeState"})
        return read(native / "time-state.json")

    try:
        report["environment"] = read(native / "environment.json")
        await command({"action": "settingsSnapshot"})
        report["settings"] = read(native / "settings.json")
        snapshot = read(native / "snapshot.json")
        assert snapshot["session"]["state"] == "Play", "Close native modals before capturing"
        assert (snapshot["width"], snapshot["height"]) == (1920, 1080), "Native 1920×1080 required"
        assert report["environment"]["actorCount"] == 9, "All nine actors must be present"
        assert report["settings"]["renderScale"] == 1, "Full native render scale required"
        if args.hour is not None:
            restore_clock = await clock_state()
            await command({"action": "timePause", "paused": True})
            await command({"action": "timeSet", "hour": args.hour})
            deadline = time.monotonic() + 30
            while True:
                state = await clock_state()
                reflections = state.get("reflections") or {}
                assert not reflections.get("failed"), "Reflection refresh failure"
                if not reflections.get("pending"):
                    report["lighting"] = state
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Reflection probes did not settle after time change")
                await asyncio.sleep(.4)
        else:
            report["lighting"] = "Current authored lighting; time state not sampled. Use --hour for a fixed day/night pass."
        for building in manifest["buildings"]:
            for view in building["views"]:
                await command({"action": "view", "camera": view["name"]})
                await asyncio.sleep(args.settle)
                before = read(native / "snapshot.json")
                assert math.dist(before["camera"]["position"], view["position"]) < .02, "Running camera position differs from saved manifest: " + view["name"]
                assert before["session"]["state"] == "Play", "A modal opened during capture"
                name = "building-audit-" + uuid.uuid4().hex
                source = native / (name + ".png")
                await command({"action": "capture", "name": name})
                deadline = time.monotonic() + 10
                while True:
                    try:
                        with Image.open(source) as im:
                            im.load()
                            assert im.size == (1920, 1080), "Capture resolution changed"
                        break
                    except (FileNotFoundError, OSError):
                        if time.monotonic() > deadline:
                            raise TimeoutError("Native image did not complete: " + str(source))
                        await asyncio.sleep(.1)
                image = view["name"] + ".png"
                shutil.copyfile(source, out / image)
                report["views"].append({"building": building["id"], "camera": view["name"], "kind": view["kind"], "image": image,
                    "sha256": digest(out / image), "width": 1920, "height": 1080, "snapshot": before,
                    "nativeCameraPositionVerified": True, "nativeRotationAndFovCounterAvailable": False,
                    "rotationAndFovBasis": "Exported saved camera; AthenDebugBridge.View copies its pose and lens. Native snapshot exposes position only.",
                    "reviewStatus": "captured, not visually reviewed"})
                write(out / "capture-report.json", report)
            print("Captured " + building["name"] + " (6 views)", flush=True)
        report["complete"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        cleanup_errors = []
        if restore_clock is not None:
            for value in [{"action": "timeSet", "hour": restore_clock["hour"]}, {"action": "timeSpeed", "speed": restore_clock["speed"]}, {"action": "timePause", "paused": restore_clock["paused"]}]:
                try:
                    await command(value)
                except Exception as error:
                    cleanup_errors.append(str(error))
        try:
            await command({"action": "view", "camera": "follow"})
        except Exception as error:
            cleanup_errors.append(str(error))
        report["cleanupErrors"] = cleanup_errors
        report["finishedUtc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write(out / "capture-report.json", report)
        captured = {r["camera"] for r in report["views"]}
        write(out / "review-ledger.json", [{"building": b["id"], "name": b["name"], "decision": "pending", "scores": None,
            "views": [{"camera": v["name"], "kind": v["kind"], "captured": v["name"] in captured,
                       "reviewed": False, "coverage": "unassessed", "defects": [], "accepted": False} for v in b["views"]]} for b in manifest["buildings"]])
        contact_sheets(out, manifest, report["views"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--build-record", required=True, type=Path, help="JSON identifying the actual tested build and saved scene")
    parser.add_argument("--output", required=True, type=Path, help="New evidence directory")
    parser.add_argument("--hour", type=float, help="Optional fixed hour; requires installed native day/night diagnostics; restores original clock state")
    parser.add_argument("--settle", type=float, default=1.0)
    args = parser.parse_args()
    if args.hour is not None and not 0 <= args.hour < 24:
        parser.error("--hour must be in [0, 24)")
    if args.settle < .3:
        parser.error("--settle must be at least 0.3 seconds")
    asyncio.run(capture(args))


if __name__ == "__main__":
    main()

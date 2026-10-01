"""Real-input Linux check for equipment drag/drop, capacity UI, and Continue."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "unity/evidence/gameplay-v2/20260930-reqa2"))
import qa  # noqa: E402


def centre(layout, name):
    element = qa.el(layout, name)
    if not element or not element["visible"]:
        raise AssertionError(f"{name} is not visible")
    x, y, w, h = element["bounds"]
    return x + w / 2, y + h / 2


def move(x, y):
    from Xlib import X
    from Xlib.ext import xtest

    display = qa._display()
    origin = display.screen().root.translate_coords(qa.window(), 0, 0)
    xtest.fake_input(display, X.MotionNotify, x=origin.x + int(x), y=origin.y + int(y))
    display.sync()
    time.sleep(0.12)


def drag(start, end):
    qa.focus(center=False)
    move(*start)
    qa.button(1, True)
    try:
        time.sleep(0.2)
        move(start[0] + 12, start[1])
        for step in range(1, 13):
            move(start[0] + (end[0] - start[0]) * step / 12,
                 start[1] + (end[1] - start[1]) * step / 12)
            if step == 6:
                if not any("equipment-drag-ghost" in element["classes"] for element in qa.ui()["elements"]):
                    raise AssertionError("equipment drag did not start")
    finally:
        qa.button(1, False)
    time.sleep(0.5)


def equipment(save):
    return {entry["slot"]: entry["itemId"] for entry in save["character"]["equipped"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    run = output / "run"
    report = {"checks": {}, "captures": []}
    qa.launch(run)
    try:
        qa.wait_menu()
        qa.tap("Return")
        qa.wait(lambda: qa.state() == "Play", 30, what="new game")
        qa.tap("Tab", settle=0.8)
        qa.wait(lambda: qa.state() == "Inventory", 5, what="inventory")
        layout = qa.ui()
        centre(layout, "character-loadout")
        report["captures"].append(qa.capture("01-inventory"))

        qa.click_at(*centre(layout, "character-tab-primary"))
        layout = qa.ui()
        drag(centre(layout, "inv-field_rifle"), centre(layout, "equipment-primary"))
        layout = qa.ui()
        report["checks"]["rifleRequirement"] = qa.el(layout, "equipment-result")["text"]
        assert qa.qty("field_rifle") == 1
        assert "Requires Rifle 20" in report["checks"]["rifleRequirement"]
        report["captures"].append(qa.capture("02-rifle-requirement"))

        qa.click_at(*centre(layout, "character-tab-implants"))
        layout = qa.ui()
        drag(centre(layout, "inv-targeting_implant_mk1"), centre(layout, "equipment-implant_head"))
        assert qa.qty("targeting_implant_mk1") == 0, "implant was not installed"
        report["captures"].append(qa.capture("03-implant-equipped"))

        qa.click_at(*centre(qa.ui(), "character-tab-stats"))
        report["captures"].append(qa.capture("04-stats-before-training"))
        for _ in range(10):
            layout = qa.ui()
            sy = qa.el(layout, "character-scroll")["bounds"][1]
            sh = qa.el(layout, "character-scroll")["bounds"][3]
            ry = centre(layout, "raise-rifle")[1]
            if sy + 20 <= ry <= sy + sh - 20:
                break
            qa.focus(center=False)
            move(*centre(layout, "character-scroll"))
            qa.button(5, True)
            qa.button(5, False)
            time.sleep(0.2)
        else:
            raise AssertionError("Rifle training button did not scroll into view")
        qa.click_at(*centre(layout, "raise-rifle"))
        assert "Improved" in qa.el(qa.ui(), "equipment-result")["text"]
        qa.click_at(*centre(qa.ui(), "character-tab-primary"))
        layout = qa.ui()
        drag(centre(layout, "inv-field_rifle"), centre(layout, "equipment-primary"))
        assert qa.qty("field_rifle") == 0, "rifle did not move out of the pack: " + qa.el(qa.ui(), "equipment-result")["text"]
        layout = qa.ui()
        report["checks"]["primary"] = qa.el(layout, "character-capacity")["text"]
        report["captures"].append(qa.capture("05-rifle-equipped"))

        drag(centre(layout, "inv-field_boots"), centre(layout, "equipment-primary"))
        assert qa.qty("field_boots") == 1, "invalid equipment drop changed inventory"
        report["checks"]["rejected"] = qa.el(qa.ui(), "equipment-result")["text"]

        qa.cmd("resize", width=1280, height=720)
        time.sleep(2)
        report["captures"].append(qa.capture("06-inventory-720"))
        qa.tap("Tab")
    finally:
        qa.stop()

    save_path = run / "save/ward-save.json"
    save = json.loads(save_path.read_text())
    report["checks"]["savedEquipment"] = equipment(save)
    assert equipment(save).get("primary") == "field_rifle"
    assert equipment(save).get("implant_head") == "targeting_implant_mk1"

    qa.launch(run)
    try:
        qa.wait_menu()
        qa.tap("Return")
        qa.wait(lambda: qa.state() == "Play", 30, what="Continue")
        qa.tap("Tab", settle=0.8)
        report["checks"]["continuedCapacity"] = qa.el(qa.ui(), "character-capacity")["text"]
        report["captures"].append(qa.capture("07-continued"))
        assert qa.qty("field_rifle") == 0
        assert qa.qty("targeting_implant_mk1") == 0
        report["checks"]["logErrors"] = qa.log_errors()
    finally:
        qa.stop()

    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    main()

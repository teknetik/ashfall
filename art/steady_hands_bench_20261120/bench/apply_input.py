#!/usr/bin/env python3
"""Adds the Bench action map (DESIGN.md section 5) to Data/Controls.inputactions. Idempotent; ids are fixed (uuid5),
the file's own formatting is kept (indent 4), nothing else in it is touched.

  python3 apply_input.py           # apply
  python3 apply_input.py --check   # exit 0 when the file already has exactly this map
  python3 apply_input.py --remove  # take the map out again (rollback)

The installer's verify step checks the result: ids unique across the asset, every Bench binding present, no key bound
to two Bench actions, nothing on the keys the always-on UI map owns (Esc, M).
"""
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.normpath(os.path.join(HERE, "..", "..", "..", "unity/AthenHill/Assets/AthenHill/Data/Controls.inputactions"))
NS = uuid.UUID("5b0a2c1e-7d4f-4e2a-9c3b-20261120be0c")


def uid(name):
    return str(uuid.uuid5(NS, name))


def action(name, kind="Button", control="", initial=False):
    return {"name": name, "type": kind, "id": uid("action/" + name), "expectedControlType": control, "processors": "", "interactions": "",
            "initialStateCheck": initial, "priority": 0}


def binding(act, path, name="", composite=False, part=False):
    return {"name": name, "id": uid("binding/%s/%s/%s" % (act, name, path)), "path": path, "interactions": "", "processors": "", "groups": "",
            "action": act, "isComposite": composite, "isPartOfComposite": part}


def bench_map():
    actions = [
        action("Pointer", "Value", "Vector2", True), action("Delta", "Value", "Vector2", True), action("Navigate", "Value", "Vector2", True),
        action("Next"), action("Primary"), action("PrimaryKey"), action("Scroll", "Value", "Axis", True), action("Rotate", "Value", "Axis", True),
        action("Flip"), action("PutBack"), action("Look"), action("LookKey"), action("Zoom", "Value", "Axis", True), action("Hint"), action("Abandon"),
    ]
    b = [binding("Pointer", "<Mouse>/position"), binding("Delta", "<Mouse>/delta")]
    for label, keys in (("WASD", ("w", "s", "a", "d")), ("Arrows", ("upArrow", "downArrow", "leftArrow", "rightArrow"))):
        b.append(binding("Navigate", "2DVector", label, composite=True))
        for part, key in zip(("Up", "Down", "Left", "Right"), keys):
            b.append(binding("Navigate", "<Keyboard>/" + key, part, part=True))
    b += [binding("Next", "<Keyboard>/tab"), binding("Primary", "<Mouse>/leftButton"),
          binding("PrimaryKey", "<Keyboard>/space"), binding("PrimaryKey", "<Keyboard>/enter"), binding("PrimaryKey", "<Keyboard>/numpadEnter"),
          binding("Scroll", "<Mouse>/scroll/y"),
          binding("Rotate", "1DAxis", "QE", composite=True), binding("Rotate", "<Keyboard>/q", "negative", part=True), binding("Rotate", "<Keyboard>/e", "positive", part=True),
          binding("Flip", "<Mouse>/middleButton"), binding("Flip", "<Keyboard>/r"), binding("PutBack", "<Keyboard>/x"),
          binding("Look", "<Mouse>/rightButton"), binding("LookKey", "<Keyboard>/leftShift"),
          binding("Zoom", "1DAxis", "ZC", composite=True), binding("Zoom", "<Keyboard>/c", "negative", part=True), binding("Zoom", "<Keyboard>/z", "positive", part=True),
          binding("Hint", "<Keyboard>/h"), binding("Abandon", "<Keyboard>/backspace")]
    return {"name": "Bench", "id": uid("map/Bench"), "actions": actions, "bindings": b}


def main():
    raw = open(PATH).read()
    data = json.loads(raw)
    assert json.dumps(data, indent=4) + "\n" == raw, "Controls.inputactions is not in the expected formatting; not touching it"
    maps = data["maps"]
    have = [m for m in maps if m["name"] == "Bench"]
    want = bench_map()
    if "--check" in sys.argv:
        ok = len(have) == 1 and have[0] == want
        print("Bench map " + ("present and current" if ok else "missing or different"))
        sys.exit(0 if ok else 1)
    data["maps"] = [m for m in maps if m["name"] != "Bench"]
    if "--remove" not in sys.argv:
        data["maps"].append(want)
    ids = [m["id"] for m in data["maps"]] + [a["id"] for m in data["maps"] for a in m["actions"]] + [b["id"] for m in data["maps"] for b in m["bindings"]]
    assert len(ids) == len(set(ids)), "duplicate ids"
    out = json.dumps(data, indent=4) + "\n"
    if out == raw:
        print("already applied")
        return
    with open(PATH, "w") as f:
        f.write(out)
    print(("removed the Bench map" if "--remove" in sys.argv else "Bench map written: %d actions, %d bindings" % (len(want["actions"]), len(want["bindings"]))))


if __name__ == "__main__":
    main()

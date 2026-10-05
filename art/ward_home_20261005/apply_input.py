#!/usr/bin/env python3
"""Ward home pass (5 Oct 2026): input actions for always-on mouse look. Idempotent; re-run after other passes edit
Controls.inputactions. Left mouse moves from the old Orbit (hold-to-look) action to Fire; adds Slot0 (key 0) and
FreeCursor (Left Alt frees the cursor during play)."""
import json, pathlib, uuid
P = pathlib.Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Data/Controls.inputactions"
d = json.loads(P.read_text())
m = next(x for x in d["maps"] if x["name"] == "Gameplay")
acts, binds = m["actions"], m["bindings"]
def action(name, guid):
    if not any(a["name"] == name for a in acts):
        acts.append({"name": name, "type": "Button", "id": guid, "expectedControlType": "", "processors": "",
                     "interactions": "", "initialStateCheck": False, "priority": 0})
def binding(name, path, guid):
    if not any(b["action"] == name and b["path"] == path for b in binds):
        binds.append({"name": "", "id": guid, "path": path, "interactions": "", "processors": "", "groups": "",
                      "action": name, "isComposite": False, "isPartOfComposite": False})
# left mouse: Orbit -> Fire (same binding id), then drop the Orbit action
for b in binds:
    if b["action"] == "Orbit" and b["path"] == "<Mouse>/leftButton": b["action"] = "Fire"
m["actions"] = acts = [a for a in acts if a["name"] != "Orbit"]
m["bindings"] = binds = [b for b in binds if b["action"] != "Orbit"]
action("Slot0", "0a7e5c31-2b4d-4f8e-9a61-5c3d2e1f0a10"); binding("Slot0", "<Keyboard>/0", "6e1d0b52-9c3a-4d7f-8b20-1f4e5a6c7d10")
action("FreeCursor", "7c2f9e14-5a3b-4c6d-8e1f-2a9b0c3d4e5f"); binding("FreeCursor", "<Keyboard>/leftAlt", "3b8d1a6e-4f2c-4a9b-9d0e-7c5f1e2a3b4c")
P.write_text(json.dumps(d, indent=4) + "\n")
print("actions:", [a["name"] for a in acts])

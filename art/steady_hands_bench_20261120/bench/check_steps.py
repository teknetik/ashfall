#!/usr/bin/env python3
"""Offline check of data/steps.json against the greybox families and data/layout.json (bench agent, 20 Nov 2026).

Every part, tool tag, bit, place, mark, path, zone, mechanism, lamp and shot a step refers to must exist; a Seat's place
must accept its part; `after`, `requires`, `replaces` and fault recoveries must name real things. It is the same check
the installer's `verify` step makes on the built bench, done without Unity so a table edit can be tested in a second.

  python3 check_steps.py            exit 1 on problems
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.normpath(os.path.join(HERE, ".."))
REPO = os.path.normpath(os.path.join(ART, "..", ".."))
GREY = os.path.join(REPO, "unity/AthenHill/Assets/AthenHill/Data/Assembly/Greybox")

steps = json.load(open(os.path.join(ART, "data/steps.json")))
layout = json.load(open(os.path.join(ART, "data/layout.json")))
parts, params, markers, tags, bits = {}, set(), {}, set(), set()
for path in sorted(glob.glob(os.path.join(GREY, "*.parts.json"))):
    fam = json.load(open(path))
    for p in fam["parts"]:
        parts[p["id"]] = p
        g = p.get("grey", {})
        for kind in ("marks", "paths", "zones"):
            for m in g.get(kind, {}):
                markers[p["id"] + "/" + m] = kind[:-1]
        for w in p.get("wipes", []):   # a wipe over the whole part: a zone no hand works (SEAM.md section 10)
            markers.setdefault(p["id"] + "/" + w["id"], "zone")
        for t in (p.get("tool") or {}).get("tags", []):
            (bits if t.startswith("bit:") else tags).add(t)
    for q in fam.get("params", []):
        params.add(q["id"])
places = {pl["id"]: pl for pl in layout["places"]}
for pid in places:
    markers.pop(pid, None)   # a mark a place is bound to is a place
lamps = {l["part"] for l in layout.get("lamps", [])}
shots = {s["id"] for s in layout["shots"]}
problems = []
all_steps = {st["id"]: st for sg in steps["stages"] for st in sg["steps"]}


def effect(where, e):
    if e.startswith("@"):   # tied to one mark of a several-mark action
        mark, e = e[1:].split(":", 1)
        if markers.get(mark) != "mark":
            problems.append("%s: effect tied to unknown mark %s" % (where, mark))
    if e.startswith("~"):   # reveals a wipe ("~part/wipe", or "~part/wipe=0.6" for a share of it)
        wipe, _, share = e[1:].partition("=")
        if markers.get(wipe) != "zone":
            problems.append("%s: effect reveals an unknown wipe %s" % (where, wipe))
        if share:
            try:
                float(share)
            except ValueError:
                problems.append("%s: effect not understood: %s" % (where, e))
        return
    if ">" in e:
        a, b = e.split(">", 1)
        if a not in parts:
            problems.append("%s: effect part %s" % (where, a))
        if b not in ("gone", "seat", "clear", "start") and b not in places:
            problems.append("%s: effect place %s" % (where, b))
        elif b in places and not ("*" in places[b]["accepts"] or a in places[b]["accepts"]):
            problems.append("%s: %s does not accept %s" % (where, b, a))
        elif b in ("seat", "clear", "start") and a in parts and b != "seat" and "clear" not in parts[a].get("seat", {}):
            problems.append("%s: %s has no clear pose" % (where, a))
    elif "=" in e:
        a = e.split("=", 1)[0]
        if a not in params and a not in lamps:
            problems.append("%s: effect mechanism or lamp %s" % (where, a))
    else:
        problems.append("%s: effect not understood: %s" % (where, e))


count = 0
for sg in steps["stages"]:
    if sg.get("shot", "wide") not in shots:
        problems.append("stage %s: shot %s" % (sg["id"], sg.get("shot")))
    for st in sg["steps"]:
        for r in st.get("requires", []):
            if r not in all_steps:
                problems.append("%s requires unknown %s" % (st["id"], r))
        for r in st.get("replaces", []):
            sid, key = r.split(":")
            if sid not in all_steps or key not in [a["key"] for a in all_steps[sid].get("actions", [])]:
                problems.append("%s replaces unknown %s" % (st["id"], r))
        if st.get("shot") and st["shot"] not in shots:
            problems.append("%s: shot %s" % (st["id"], st["shot"]))
        for e in st.get("effects", []):
            effect(st["id"], e)
        keys = [a["key"] for a in st.get("actions", [])]
        if len(keys) != len(set(keys)):
            problems.append("%s: duplicate action keys" % st["id"])
        for a in st.get("actions", []):
            count += 1
            where = st["id"] + ":" + a["key"]
            part = a.get("part", "")
            if part and part not in parts:
                problems.append("%s: part %s" % (where, part))
            tool = a.get("tool", "")
            if tool and tool != "*" and tool not in tags and tool not in parts:
                problems.append("%s: tool %s" % (where, tool))
            if a.get("toolMode") and "bit:" + a["toolMode"] not in bits:
                problems.append("%s: no bit %s" % (where, a["toolMode"]))
            target = a.get("target", "")
            verb = a["verb"]
            if target and target not in ("seat", "start", "clear") and target not in places and target not in markers and target not in parts:
                problems.append("%s: target %s" % (where, target))
            if verb == "Seat" and a.get("mode") != "inspect":
                if target in places and not ("*" in places[target]["accepts"] or part in places[target]["accepts"]):
                    problems.append("%s: %s does not accept %s" % (where, target, part))
                if target in ("seat", "start", "clear") and part in parts and "clear" not in parts[part].get("seat", {}):
                    problems.append("%s: %s has no clear pose" % (where, part))
                if not target:
                    problems.append("%s: Seat without a target" % where)
            if verb == "Path" and markers.get(target) != "path":
                problems.append("%s: %s is not a path" % (where, target))
            if verb == "Wipe" and markers.get(target) != "zone":
                problems.append("%s: %s is not a zone" % (where, target))
            for t in a.get("targets", []):
                if markers.get(t) != "mark":
                    problems.append("%s: %s is not a mark" % (where, t))
            if a.get("drive") and a["drive"] not in params and not (a.get("mode") == "sustain" and a["drive"] in lamps):
                problems.append("%s: mechanism %s" % (where, a["drive"]))
            if a.get("shot") and a["shot"] not in shots:
                problems.append("%s: shot %s" % (where, a["shot"]))
            for k in a.get("after", []):
                if k not in keys:
                    problems.append("%s: after unknown %s" % (where, k))
            for e in a.get("effects", []):
                effect(where, e)
            for f in a.get("faults", []):
                if f.get("recovery") and (f["recovery"] not in all_steps or not all_steps[f["recovery"]].get("recovery")):
                    problems.append("%s: fault %s names no recovery step %s" % (where, f["kind"], f.get("recovery")))
                for e in f.get("effects", []):
                    effect(where + " fault " + f["kind"], e)
for pid, where in layout["home"].items():
    if where != "gone" and not ("*" in places[where]["accepts"] or pid in places[where]["accepts"]):
        problems.append("home: %s does not accept %s" % (where, pid))
rows = sum(1 for st in all_steps.values() if not st.get("recovery"))
print("%d steps (%d design rows), %d actions, %d parts, %d places, %d marks/paths/zones" % (len(all_steps), rows, count, len(parts), len(places), len(markers)))
for p in problems:
    print("PROBLEM " + p)
sys.exit(1 if problems else 0)

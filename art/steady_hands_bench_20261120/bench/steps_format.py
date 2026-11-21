#!/usr/bin/env python3
"""Reads and writes data/steps.json in its compact form: one action per line, one step header per line.
The table is edited by hand or by small scripts that import this; `python3 steps_format.py --check` proves that a
load and a dump give the file back unchanged (run it before and after a scripted edit)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "data", "steps.json")
J = lambda o: json.dumps(o, ensure_ascii=False)


def load(path=PATH):
    return json.load(open(path, encoding="utf-8"))


def dumps(table):
    head = {k: v for k, v in table.items() if k != "stages"}
    out = ["{"]
    for k, v in head.items():
        out.append(" %s: %s," % (J(k), J(v)))
    out.append(' "stages": [')
    stages = table["stages"]
    for si, stage in enumerate(stages):
        sh = {k: v for k, v in stage.items() if k != "steps"}
        out.append("  " + J(sh)[:-1] + ', "steps": [')
        steps = stage["steps"]
        for i, st in enumerate(steps):
            acts = st.get("actions", [])
            h = J({k: v for k, v in st.items() if k != "actions"})[:-1]
            comma = "," if i < len(steps) - 1 else ""
            if acts:
                out.append("   " + h + ', "actions": [')
                out.append(",\n".join("    " + J(a) for a in acts) + "]}" + comma)
            else:
                out.append("   " + h + "}" + comma)
        out.append("  ]}" + ("," if si < len(stages) - 1 else ""))
    out.append(" ]")
    out.append("}")
    return "\n".join(out) + "\n"


def save(table, path=PATH):
    text = dumps(table)
    json.loads(text)
    open(path, "w", encoding="utf-8").write(text)


def steps(table):
    for stage in table["stages"]:
        for st in stage["steps"]:
            yield stage, st


def step(table, sid):
    for _, st in steps(table):
        if st["id"] == sid:
            return st
    raise KeyError(sid)


def action(table, sid, key):
    for a in step(table, sid)["actions"]:
        if a.get("key") == key:
            return a
    raise KeyError(sid + ":" + key)


if __name__ == "__main__":
    t = load()
    same = dumps(t) == open(PATH, encoding="utf-8").read()
    n = sum(len(st.get("actions", [])) for _, st in steps(t))
    print("%d stages, %d steps, %d actions; round trip %s" % (len(t["stages"]), sum(1 for _ in steps(t)), n, "identical" if same else "DIFFERS"))
    if "--write" in sys.argv:
        save(t)
    sys.exit(0 if same or "--write" in sys.argv else 1)

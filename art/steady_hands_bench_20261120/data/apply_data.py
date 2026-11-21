#!/usr/bin/env python3
"""Steady Hands bench data patch (craft agent, 20 Nov 2026). Idempotent and exact-match: every edit is skipped when it
is already applied and fails loudly when its anchor is missing (the asset changed under us).

  python3 art/steady_hands_bench_20261120/data/apply_data.py          # apply
  python3 art/steady_hands_bench_20261120/data/apply_data.py --check  # report only, exit 1 if anything is unapplied

What it sets (WardCrafting.asset unless noted):
  - recipe_grip_stabilised_pistol.assembly = assembly_grip_stabilised_pistol (the hands-on job; timer after one by hand)
  - weapon handling stats sway / sideKick / recovery / scatterGrowth on every weapon's stats, minStats and maxStats
    (the scrap pistol gets its rough numbers; other weapons 0 = unchanged feel)
  - the Stabilised Pistol Grip's effects by crafted quality (Rough / Standard / Fine) and the Mark II grip's handling
  - stat labels for the four handling stats (Fabricator table, loadout panel)
  WardFieldOrders.asset: the bench objective and journal step; Steady Hands' judged three-shot test fire after a bench
    build with Ossa's range lines (captions; from audio/lines.json); npc_brann.asset: steady_bench_open (job waiting).
Numbers and what each does on screen: art/steady_hands_bench_20261120/craft/README.md.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "unity/AthenHill/Assets/AthenHill"
CRAFT = A / "Data/Crafting/WardCrafting.asset"
CHECK = "--check" in sys.argv
pending = []

# ---- numbers (data; tuned in play) -------------------------------------------------------------------------------------
HANDLING = ("sway", "sideKick", "recovery", "scatterGrowth")
PISTOL = {"sway": 1.2, "sideKick": 0.9, "recovery": 0.34, "scatterGrowth": 0.35}
MAXIMA = {"sway": 20, "sideKick": 20, "recovery": 5, "scatterGrowth": 5}
# Stabilised Pistol Grip effects: (stat, Rough, Standard, Fine), all "add"
GRIP = [("recoil", -5, -7, -10), ("sway", -0.6, -0.75, -0.95), ("sideKick", -0.5, -0.7, -0.82),
        ("recovery", -0.1, -0.16, -0.2), ("scatterGrowth", -0.17, -0.23, -0.28)]
# Mark II gyro grip (timed craft, always Standard): at least as steady as a Fine Mark I
GYRO = [("sway", -0.98), ("sideKick", -0.84), ("recovery", -0.2), ("scatterGrowth", -0.29)]
LABELS = [("sway", "Aim sway", "0.00", "\\xB0"), ("sideKick", "Side kick", "0.00", "\\xB0"),
          ("recovery", "Recovery", "0.00", "' s'"), ("scatterGrowth", "Rapid-fire scatter", "0%", "")]


def num(v):
    return ("%g" % v)


def edit(label, fn):
    text = CRAFT.read_text()
    new = fn(text)
    if new == text:
        print(f"ok      {label}")
        return
    pending.append(label)
    print(f"{'WOULD  ' if CHECK else 'applied'} {label}")
    if not CHECK:
        CRAFT.write_text(new)


def replace_once(text, old, new, label, applied):
    if applied in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f"anchor for '{label}' found {text.count(old)}x; not patching")
    return text.replace(old, new, 1)


# ---- recipe: the hands-on job ------------------------------------------------------------------------------------------
def recipe(text):
    block = re.search(r"  - id: recipe_grip_stabilised_pistol\n(?:    .*\n|    \n)+", text)
    if not block:
        raise SystemExit("recipe_grip_stabilised_pistol not found")
    b = block.group(0)
    if "    assembly: assembly_grip_stabilised_pistol\n" in b:
        return text
    if "    assembly:" in b:
        nb = re.sub(r"    assembly:.*\n", "    assembly: assembly_grip_stabilised_pistol\n", b)
    else:
        if not b.endswith("    skillUse: 1\n"):
            raise SystemExit("recipe_grip_stabilised_pistol does not end with skillUse: 1; not patching")
        nb = b + "    assembly: assembly_grip_stabilised_pistol\n"
    return text.replace(b, nb, 1)


edit("recipe_grip_stabilised_pistol: assembly", recipe)


# ---- weapons: handling stats -------------------------------------------------------------------------------------------
def weapons(text):
    start = text.index("  weapons:\n")
    end = text.index("  modifiers:\n")
    section = text[start:end]
    blocks = re.split(r"(?=^  - id: )", section, flags=re.M)
    out = []
    for blk in blocks:
        m = re.match(r"  - id: (\S+)", blk)
        if not m:
            out.append(blk)
            continue
        wid = m.group(1)
        def fill(kind, values):
            nonlocal blk
            pat = re.compile(r"(    %s:\n(?:      \w+: .*\n)+)" % kind)
            mm = pat.search(blk)
            if not mm:
                raise SystemExit(f"{wid}.{kind} not found")
            body = mm.group(1)
            if "      sway:" in body:
                return
            if not body.rstrip("\n").split("\n")[-1].startswith("      armourPenetration:"):
                raise SystemExit(f"{wid}.{kind} does not end with armourPenetration")
            add = "".join(f"      {k}: {num(values[k])}\n" for k in HANDLING)
            blk = blk.replace(body, body + add, 1)
        fill("stats", PISTOL if wid == "weapon_scrap_pistol" else dict.fromkeys(HANDLING, 0))
        fill("minStats", dict.fromkeys(HANDLING, 0))
        fill("maxStats", MAXIMA)
        out.append(blk)
    return text[:start] + "".join(out) + text[end:]


edit("weapons: handling stats (pistol rough, others 0)", weapons)


# ---- grip mods: effects by quality -------------------------------------------------------------------------------------
def effects_yaml(rows, by_quality):
    s = "    effects:\n"
    for row in rows:
        stat = row[0]
        if by_quality:
            r, st, f = row[1:]
            s += f"    - stat: {stat}\n      op: add\n      value: {num(st)}\n      byQuality:\n      - {num(r)}\n      - {num(st)}\n      - {num(f)}\n"
        else:
            s += f"    - stat: {stat}\n      op: add\n      value: {num(row[1])}\n"
    return s


GRIP_OLD = """  - id: mod_grip_stabilised
    itemId: grip_stabilised_pistol
    slot: grip
    weaponIds:
    - weapon_scrap_pistol
    effects:
    - stat: recoil
      op: add
      value: -7
    requirements: []"""
GRIP_NEW = """  - id: mod_grip_stabilised
    itemId: grip_stabilised_pistol
    slot: grip
    weaponIds:
    - weapon_scrap_pistol
""" + effects_yaml(GRIP, True) + "    requirements: []"
edit("mod_grip_stabilised: effects by quality", lambda t: replace_once(t, GRIP_OLD, GRIP_NEW, "mod_grip_stabilised", GRIP_NEW))

GYRO_OLD = """  - id: mod_grip_gyro_braced
    itemId: grip_gyro_braced
    slot: grip
    weaponIds:
    - weapon_scrap_pistol
    effects:
    - stat: recoil
      op: add
      value: -15
    - stat: aimAssist
      op: add
      value: 1
    requirements: []"""
GYRO_NEW = GYRO_OLD.replace("    requirements: []", effects_yaml(GYRO, False).replace("    effects:\n", "") + "    requirements: []")
edit("mod_grip_gyro_braced: handling", lambda t: replace_once(t, GYRO_OLD, GYRO_NEW, "mod_grip_gyro_braced", GYRO_NEW))


# ---- stat labels -------------------------------------------------------------------------------------------------------
def labels(text):
    if "  - stat: sway\n    label:" in text:
        return text
    if not text.rstrip("\n").endswith("    lowerIsBetter: 1") or "  statLabels:\n" not in text:
        raise SystemExit("statLabels is not the last list in WardCrafting.asset; not patching")
    add = ""
    for stat, label, fmt, unit in LABELS:
        u = unit if unit.startswith("'") else (f'"{unit}"' if unit else "")
        add += f"  - stat: {stat}\n    label: {label}\n    format: {fmt}\n    unit: {u}\n    lowerIsBetter: 1\n"
    return text.rstrip("\n") + "\n" + add


edit("statLabels: handling", labels)

# ---- field orders (WardFieldOrders.asset): the bench route's objective and journal step, the judged test fire ------------
ORDERS = A / "Data/Crafting/WardFieldOrders.asset"
LINES = ROOT / "art/steady_hands_bench_20261120/audio/lines.json"


def line_text(line_id, speaker, fallback):
    """Text of an audio-agent line (caption = text), so the radio caption matches the take when it is voiced later."""
    try:
        import json
        for l in json.loads(LINES.read_text())["lines"]:
            if l["id"] == line_id and l["speaker"] == speaker:
                return l["text"]
    except Exception:
        pass
    return fallback


def yq(s):
    return "'" + s.replace("'", "''") + "'"


def edit_file(path, label, fn):
    text = path.read_text()
    new = fn(text)
    if new == text:
        print(f"ok      {label}")
        return
    pending.append(label)
    print(f"{'WOULD  ' if CHECK else 'applied'} {label}")
    if not CHECK:
        path.write_text(new)


TEST_READY = line_text("range_ready", "npc_ossa", "Brann says it's steady. Show me. Three on the plate.")
TEST_TIGHT = line_text("range_tight", "npc_ossa", "Tight. That pistol's finally pulling its weight.")
TEST_POOR = line_text("range_poor", "npc_ossa", "Wide. Breathe out, then squeeze. Again.")
TEST_DONE = line_text("range_done", "npc_ossa", "Steady. I'll log the order. Keep that grip clean.")


def steady_order(text):
    m = __import__("re").search(r"  - id: order_steady_hands\n(?:    .*\n)+", text)
    if not m:
        raise SystemExit("order_steady_hands not found")
    b = m.group(0)
    nb = b
    if "    testFireShots:" not in nb:
        anchor = "    completeLine: Stabilised grip tested. Your pistol holds steadier.\n"
        if anchor not in nb:
            raise SystemExit("order_steady_hands completeLine anchor missing; not patching")
        nb = nb.replace(anchor, f"    completeLine: {yq(TEST_DONE)}\n    testFireShots: 3\n    testFireTightDegrees: 3.5\n"
                        f"    testFireLine: {yq(TEST_READY)}\n    testFireTightLine: {yq(TEST_TIGHT)}\n    testFirePoorLine: {yq(TEST_POOR)}\n")
    return text.replace(b, nb, 1)


def order_set(text):
    if "  benchFormat:" in text:
        return text
    anchor = "  fitFormat: "
    if text.count(anchor) != 1:
        raise SystemExit("fitFormat anchor missing in WardFieldOrders.asset")
    add = ("  benchFormat: 'Build and fit the {item} at Brann''s bench in Salvage, on the north avenue.\n\n    {stage}'\n"
           "  benchStepFormat: Build and fit the {item} at Brann's bench\n")
    return text.replace(anchor, add + anchor, 1)


edit_file(ORDERS, "order_steady_hands: judged test fire and Ossa's range lines", steady_order)
edit_file(ORDERS, "field orders: bench objective and journal step", order_set)


# ---- Brann: a line when the bench job is waiting (voice bound when the audio agent's take exists) ----------------------
BRANN = A / "Data/npc_brann.asset"


def voice_ref(rel):
    meta = ROOT / "unity/AthenHill" / (rel + ".meta")
    if not meta.exists():
        return "{fileID: 0}"
    guid = [l.split(":")[1].strip() for l in meta.read_text().splitlines() if l.startswith("guid:")][0]
    return "{fileID: 8300000, guid: %s, type: 3}" % guid


COME_BACK = line_text("come_back", "npc_brann", "Pick up where you left off.")
COME_BACK_FILE = "Assets/AthenHill/Audio/ElevenLabs/Bench/Voice/npc_brann-come_back.wav"


def brann(text):
    entry_anchor = "  - node: steady_bench\n    requires: order:order_steady_hands, stage:Fabricate\n"
    if "  - node: steady_bench_open\n" not in text:
        if text.count(entry_anchor) != 1:
            raise SystemExit("Brann steady_bench entry anchor missing")
        text = text.replace(entry_anchor, "  - node: steady_bench_open\n    requires: order:order_steady_hands, bench\n" + entry_anchor, 1)
    voice = voice_ref(COME_BACK_FILE)
    if "  - id: steady_bench_open\n" not in text:
        node_anchor = "  - id: steady_bench\n    title: Steady Hands\n"
        if text.count(node_anchor) != 1:
            raise SystemExit("Brann steady_bench node anchor missing")
        node = ("  - id: steady_bench_open\n    title: Steady Hands\n"
                f"    text: {yq(COME_BACK)}\n    voice: {voice}\n    choices:\n"
                "    - id: fabricator_630\n      label: Back to the bench.\n      next: \n      action: fabricator\n      requires: pistol\n      setFlag: \n"
                "    - id: close_93\n      label: Later, Brann.\n      next: \n      action: close\n      requires: \n      setFlag: \n")
        text = text.replace(node_anchor, node + node_anchor, 1)
    elif voice != "{fileID: 0}" and "  - id: steady_bench_open\n    title: Steady Hands\n    text: " in text:
        import re
        text = re.sub(r"(  - id: steady_bench_open\n    title: Steady Hands\n    text: .*\n    voice: )\{fileID: 0\}", lambda m: m.group(1) + voice, text)
    # the bench is never offered before the pistol is carried (SalvageShopTests); fixes the first version of this node
    text = text.replace("      label: Back to the bench.\n      next: \n      action: fabricator\n      requires: \n",
                        "      label: Back to the bench.\n      next: \n      action: fabricator\n      requires: pistol\n")
    return text


edit_file(BRANN, "npc_brann: steady_bench_open (bench job waiting)", brann)


# ---- voiced takes (audio agent): Ossa's range lines on Steady Hands, the handling sounds on the crafting catalog -------
def ossa_voices(text):
    import re
    m = re.search(r"  - id: order_steady_hands\n(?:    .*\n)+", text)
    b = m.group(0)
    refs = {"testFireVoice": "range_ready", "testFireTightVoice": "range_tight", "testFirePoorVoice": "range_poor", "completeVoice": "range_done"}
    nb = b
    for field, line_id in refs.items():
        ref = voice_ref(f"Assets/AthenHill/Audio/ElevenLabs/Bench/Voice/npc_ossa-{line_id}.wav")
        if f"    {field}:" in nb:
            if ref != "{fileID: 0}":
                nb = re.sub(rf"    {field}: .*\n", f"    {field}: {ref}\n", nb)
        else:
            anchor = "    testFirePoorLine: "
            i = nb.index(anchor); j = nb.index("\n", i) + 1
            nb = nb[:j] + f"    {field}: {ref}\n" + nb[j:]
    return text.replace(b, nb, 1)


edit_file(ORDERS, "order_steady_hands: Ossa's range takes", ossa_voices)

# The judged string is fired from the Warden training range's firing line (fix round, 20 Nov 2026). Centre of the three
# firing bays: art/training_range_20261001/layout.py frame F = checkpoint_firingline (-66.2, 7.6), yaw -63, bays at lat
# 0 / 1.6 / 3.2 m to the right (NNE) -> bay 2 at (-65.47, 9.03); 4 m covers all three bays and the step behind them.
RANGE_AT = "{x: -65.47, y: -1.46, z: 9.03}"
RANGE_R = "4"
RANGE_BRIEF = "Test the {item} at the Warden range: stand at the firing line by Ossa's post and put three shots on the plates."
RANGE_STEP = "Test-fire it from the Warden range's firing line"


def range_fields(text):
    import re
    m = re.search(r"  - id: order_steady_hands\n(?:    .*\n)+", text)
    b = m.group(0)
    if "    testFireAt:" in b:
        return text
    anchor = "    testFireShots: 3\n"
    if anchor not in b:
        raise SystemExit("order_steady_hands testFireShots anchor missing")
    nb = b.replace(anchor, anchor + f"    testFireAt: {RANGE_AT}\n    testFireRadius: {RANGE_R}\n    testFireBrief: {yq(RANGE_BRIEF)}\n"
                   f"    testFireStep: {RANGE_STEP}\n    testFireLabel: FIRING LINE\n", 1)
    return text.replace(b, nb, 1)


edit_file(ORDERS, "order_steady_hands: test fire at the range's firing line", range_fields)

SOUNDS = {"rattleClips": [f"Assets/AthenHill/Audio/ElevenLabs/Bench/rattle/rattle-shake-0{i}.wav" for i in (1, 2, 3)],
          "damperClips": [f"Assets/AthenHill/Audio/ElevenLabs/Bench/damper/damper-tick-0{i}.wav" for i in (1, 2, 3, 4)]}


def handling_sounds(text):
    import re
    for field, files in SOUNDS.items():
        refs = [voice_ref(f) for f in files]
        refs = [r for r in refs if r != "{fileID: 0}"]
        block = f"  {field}:\n" + "".join(f"  - {r}\n" for r in refs) if refs else f"  {field}: []\n"
        if re.search(rf"^  {field}:", text, re.M):
            text = re.sub(rf"^  {field}:(?: \[\])?\n(?:  - .*\n)*", block, text, count=1, flags=re.M)
        else:
            anchor = "  statLabels:\n"
            if text.count(anchor) != 1:
                raise SystemExit("statLabels anchor missing")
            text = text.replace(anchor, block + anchor, 1)
    return text


edit("crafting catalog: rattle and damper clips", handling_sounds)

if CHECK:
    print(f"{len(pending)} unapplied" if pending else "all applied")
    sys.exit(1 if pending else 0)

#!/usr/bin/env bash
# Renders the five unrigged 27 Sep 2026 Meshy roster models (meshy/npc-roster-20260927) for the Meshy-blocked fallback.
for n in salvage_hauler ward_townswoman karaveen_trader_m karaveen_trader_f hydroponics_worker; do
  /home/teknetik/.local/state/ward-programme/showcase-phase2-20261120/blender.sh /home/teknetik/code/ao2/meshy/ward-residents-20261120/inspect_npc.py -- /home/teknetik/code/ao2/meshy/npc-roster-20260927/$n textured 2>&1 | grep -E "INSPECT|Error"
done

#!/usr/bin/env python3
"""Compact before -> after table (means, with max) from a CharacterArmsPass20261120 survey.json, as Markdown.
Usage: python3 summary_table.py SURVEY_JSON [clip_slots=idle,walk,run,talk]"""
import json, sys

data = json.load(open(sys.argv[1]))
slots = (sys.argv[2] if len(sys.argv) > 2 else 'idle,walk,run,talk').split(',')
keys = [('abduction', 'arm out'), ('forward', 'reach fwd'), ('elbowFlex', 'elbow bend'), ('elbowOut', 'elbow out'), ('palm', 'palm'), ('wrist', 'wrist'), ('shoulderLift', 'shoulder lift cm'), ('handOut', 'hand out cm')]
print('| character | clip | ' + ' | '.join(k[1] for k in keys) + ' |')
print('|---|---|' + '---|' * len(keys))
for a in data['actors']:
    for c in a['clips']:
        if c['slot'] not in slots or not c.get('after'):
            continue
        cells = []
        for k, _ in keys:
            b, af = c['before'].get(k), c['after'].get(k)
            if not b or not af:
                cells.append('-'); continue
            cells.append(f"{b['mean']:.0f} ({b['max']:.0f}) → {af['mean']:.0f} ({af['max']:.0f})")
        print(f"| {a['rig']['label']} | {c['slot']} | " + ' | '.join(cells) + ' |')

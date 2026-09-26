"""Compare all four saved AmbientWalker components and their complete route chains.

Read-only with respect to Unity: parses the baseline and current scene YAML,
records exact serialized-document hashes and relevant properties, and writes only
the dated evidence JSON. Route parent transforms and prefab instance overrides
are included, so unchanged local waypoints alone cannot imply unchanged routes.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'unity/evidence/reference-street/20260909'
BEFORE = EVIDENCE / 'before-scene.unity'
AFTER = ROOT / 'unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity'
META = ROOT / 'unity/AthenHill/Assets/AthenHill/Scripts/AmbientWalker.cs.meta'


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def documents(path):
    text = path.read_text()
    heads = list(re.finditer(r'^--- !u!(\d+) &(-?\d+)( stripped)?\n', text, re.M))
    return {m.group(2): {'type': int(m.group(1)), 'stripped': bool(m.group(3)),
                        'text': text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)].rstrip()}
            for i, m in enumerate(heads)}


def field(doc, key):
    match = re.search(r'^  ' + re.escape(key) + r': (.*)$', doc['text'], re.M)
    return match.group(1) if match else None


def reference(doc, key):
    value = field(doc, key)
    match = re.search(r'fileID: (-?\d+)', value or '')
    return match.group(1) if match else None


def waypoint_ids(doc):
    match = re.search(r'^  waypoints:\n((?:  - .*\n)+)', doc['text'] + '\n', re.M)
    assert match, 'AmbientWalker has no serialized waypoint references.'
    return re.findall(r'fileID: (-?\d+)', match.group(1))


def describe(doc):
    keys = ['m_Name', 'm_IsActive', 'm_Enabled', 'm_GameObject', 'm_PrefabInstance',
            'm_CorrespondingSourceObject', 'm_LocalPosition', 'm_LocalRotation',
            'm_LocalScale', 'm_Father', 'speed', 'phase', 'turnLookAhead', 'turnSharpness', 'actor']
    return {k: value for k in keys if (value := field(doc, k)) is not None}


def collect_dependencies(scene, walker_id):
    """Follow route ancestors, GameObjects, and corresponding prefab overrides."""
    pending = [walker_id, *waypoint_ids(scene[walker_id])]
    collected = set()
    while pending:
        key = pending.pop()
        if key in collected or key in {None, '0'}:
            continue
        assert key in scene, 'Missing referenced serialized document ' + str(key)
        collected.add(key)
        doc = scene[key]
        pending.extend([reference(doc, 'm_GameObject'), reference(doc, 'm_Father'),
                        reference(doc, 'm_PrefabInstance')])
        if doc['type'] == 1:
            # Include each actor/route GameObject's Transform, without following
            # unrelated visual components that this narrowly scoped audit does not prove.
            pending.extend(other_id for other_id, other in scene.items()
                           if other['type'] == 4 and reference(other, 'm_GameObject') == key)
    return collected


def main():
    before = documents(BEFORE)
    after = documents(AFTER)
    guid = re.search(r'^guid: (\w+)', META.read_text(), re.M).group(1)
    def walkers(scene):
        return {key for key, doc in scene.items() if doc['type'] == 114
                and ('guid: ' + guid + ',') in doc['text']}
    old_ids, new_ids = walkers(before), walkers(after)
    report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  scope=__doc__, beforeScene=str(BEFORE.relative_to(ROOT)), afterScene=str(AFTER.relative_to(ROOT)),
                  beforeSceneSha256=sha(BEFORE.read_bytes()), afterSceneSha256=sha(AFTER.read_bytes()),
                  walkerScriptGuid=guid, beforeWalkerCount=len(old_ids), afterWalkerCount=len(new_ids),
                  sameWalkerComponentIds=old_ids == new_ids, actors=[], complete=False)
    all_equal = old_ids == new_ids
    for key in sorted(old_ids | new_ids, key=int):
        if key not in before or key not in after:
            report['actors'].append(dict(componentFileId=key, presentBefore=key in before, presentAfter=key in after))
            all_equal = False
            continue
        old, new = before[key], after[key]
        old_refs, new_refs = collect_dependencies(before, key), collect_dependencies(after, key)
        checks = []
        for dep in sorted(old_refs | new_refs, key=int):
            a, b = before.get(dep), after.get(dep)
            equal = bool(a and b and a['text'] == b['text'])
            all_equal = all_equal and equal
            checks.append(dict(fileId=dep, unityType=a['type'] if a else b['type'],
                               beforeSha256=sha(a['text']) if a else None,
                               afterSha256=sha(b['text']) if b else None, identical=equal,
                               beforeProperties=describe(a) if a else None,
                               afterProperties=describe(b) if b else None))
        entry = dict(componentFileId=key, gameObjectFileId=reference(old, 'm_GameObject'),
                     waypointIdsBefore=waypoint_ids(old), waypointIdsAfter=waypoint_ids(new),
                     propertiesBefore=describe(old), propertiesAfter=describe(new),
                     sameDependencyIds=old_refs == new_refs, serializedDocuments=checks,
                     allComparedDocumentsIdentical=old_refs == new_refs and all(c['identical'] for c in checks))
        all_equal = all_equal and entry['allComparedDocumentsIdentical']
        report['actors'].append(entry)
    report['allFourWalkersAndRouteChainsPreserved'] = len(old_ids) == len(new_ids) == 4 and all_equal
    report['complete'] = True
    output = EVIDENCE / 'actor-route-preservation.json'
    assert not output.exists(), 'Preserve the existing audit; use a new filename for later revisions.'
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in {'scope', 'actors'}}, indent=2))
    assert report['allFourWalkersAndRouteChainsPreserved'], 'Recorded preservation mismatch requires inspection.'


if __name__ == '__main__':
    main()

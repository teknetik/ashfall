"""Versioned, strictly validated draft design data; never Unity runtime state."""
import math
import re

ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
TAG = re.compile(r"^[a-z][a-z0-9_:]{1,63}$")
MAX_ITEMS = 1000


def seed():
    def item(id, name, category, tags, **kw):
        return dict(id=id, name=name, category=category, subtype=kw.get('subtype', ''), tier=1,
                    rarity='Common', weightKg=kw.get('weightKg', 0), stack=kw.get('stack', 20),
                    tags=tags, stats=kw.get('stats', {}))
    return dict(schemaVersion=1, source='draft', items=[
        item('weapon_scrap_pistol', 'Scrap pistol (design reference)', 'Weapon', ['weapon:pistol'], stats={'recoil': 38}),
        item('droid_servo_damaged', 'Damaged droid servo', 'Component', ['component:servo', 'droid', 'salvage'], weightKg=.35),
        item('scrap_alloy', 'Scrap alloy', 'Material', ['material:alloy', 'salvage']),
        item('nanite_residue', 'Nanite residue', 'Material', ['nanite:tier1', 'salvage']),
        item('copper_filament', 'Copper filament', 'Material', ['material:conductive', 'salvage']),
        item('micro_capacitor', 'Micro capacitor', 'Component', ['electronic', 'salvage']),
        item('grip_stabilised_pistol', 'Stabilised pistol grip', 'Upgrade', ['component:grip', 'weapon:pistol'], stats={'recoil': -7}),
        item('cracked_ceramic_bearing', 'Cracked ceramic bearing', 'Junk', ['salvage']),
    ], recipes=[dict(id='recipe_grip_stabilised_pistol', name='Stabilised pistol grip',
                    station='station_field_fabricator', seconds=3,
                    inputs=[dict(kind='tag', ref='component:servo', quantity=1), dict(kind='item', ref='scrap_alloy', quantity=2), dict(kind='tag', ref='nanite:tier1', quantity=5)],
                    outputs=[dict(itemId='grip_stabilised_pistol', quantity=1)])],
        enemies=[dict(id='feral_worker_droid', name='Feral worker droid', loot=[
            dict(itemId='scrap_alloy', min=1, max=2, chance=100), dict(itemId='droid_servo_damaged', min=1, max=1, chance=100),
            dict(itemId='nanite_residue', min=2, max=3, chance=100)]),
            dict(id='feral_scrap_drone', name='Feral scrap drone', loot=[
                dict(itemId='scrap_alloy', min=1, max=1, chance=100), dict(itemId='nanite_residue', min=2, max=2, chance=100)])])


def validate(data):
    errors = []
    if not isinstance(data, dict) or set(data) != {'schemaVersion', 'source', 'items', 'recipes', 'enemies'} or data.get('schemaVersion') != 1 or data.get('source') != 'draft':
        return ['Expected exact draft schemaVersion 1 with items, recipes and enemies.']
    for kind in ('items', 'recipes', 'enemies'):
        if not isinstance(data[kind], list) or len(data[kind]) > MAX_ITEMS:
            return [f'{kind} must be an array of at most {MAX_ITEMS}.']
    ids = {}
    def check_id(value, where):
        if not isinstance(value, str) or not ID.fullmatch(value): errors.append(f'{where}: invalid stable ID')
        return isinstance(value, str) and bool(ID.fullmatch(value))
    def number(value, where, low=0, high=100000, integer=False):
        if type(value) not in (int, float) or (integer and type(value) is not int) or not math.isfinite(value) or not low <= value <= high:
            errors.append(f'{where}: expected {"integer " if integer else "number "}{low}..{high}')
    for kind in ('items', 'recipes', 'enemies'):
        for i, row in enumerate(data[kind]):
            w = f'{kind}[{i}]'
            if not isinstance(row, dict): errors.append(f'{w}: expected object'); continue
            rid = row.get('id')
            if check_id(rid, w):
                if rid in ids: errors.append(f'{w}: duplicate ID {rid}')
                ids[rid] = kind
            if not isinstance(row.get('name'), str) or not 1 <= len(row['name']) <= 120: errors.append(f'{w}: name required (1..120 chars)')
    items = {x['id']: x for x in data['items'] if isinstance(x, dict) and isinstance(x.get('id'), str)}
    graph = {i: set() for i in items}
    for i, x in enumerate(data['items']):
        if not isinstance(x, dict): continue
        w = f'items[{i}]'
        required = {'id','name','category','subtype','tier','rarity','weightKg','stack','tags','stats'}
        optional = {'description','designNotes','buyPrice','sellPrice','iconAsset','aiProvenance','equipment'}
        if not required <= set(x) or set(x) - required - optional: errors.append(f'{w}: unexpected or missing fields')
        for field, limit in [('description', 1200), ('designNotes', 2000)]:
            if field in x and (not isinstance(x[field], str) or len(x[field]) > limit): errors.append(f'{w}.{field}: invalid text')
        for field in ('buyPrice', 'sellPrice'):
            if field in x: number(x[field], w+'.'+field, 0, 1000000, True)
        if 'iconAsset' in x and (not isinstance(x['iconAsset'], str) or not re.fullmatch(r'/api/ai/assets/[0-9a-f]{32}\.png', x['iconAsset'])):
            errors.append(f'{w}.iconAsset: expected a local generated PNG')
        if 'aiProvenance' in x and (not isinstance(x['aiProvenance'], list) or len(x['aiProvenance']) > 32 or any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{32}', v) for v in x['aiProvenance'])):
            errors.append(f'{w}.aiProvenance: expected at most 32 generation IDs')
        if 'equipment' in x:
            equipment = x['equipment']
            if not isinstance(equipment, dict) or set(equipment) != {'kind','slots','socketTypes','modificationSockets','modifiers'}:
                errors.append(f'{w}.equipment: invalid equipment definition')
            else:
                if equipment['kind'] not in ('implant','armour','augmentation','armour_mod'): errors.append(f'{w}.equipment: unsupported kind')
                for field in ('slots','socketTypes'):
                    values = equipment[field]
                    if not isinstance(values, list) or len(values) > 16 or any(not isinstance(v, str) or not ID.fullmatch(v) for v in values) or len(set(v for v in values if isinstance(v,str))) != len(values):
                        errors.append(f'{w}.equipment.{field}: invalid IDs')
                if equipment['kind'] in ('implant', 'armour') and not equipment['slots']:
                    errors.append(f'{w}.equipment: equipment hosts need at least one body slot')
                if equipment['kind'] in ('augmentation', 'armour_mod') and not equipment['socketTypes']:
                    errors.append(f'{w}.equipment: components need a compatible socket type')
                sockets = equipment['modificationSockets']
                if not isinstance(sockets, list) or len(sockets) > 8:
                    errors.append(f'{w}.equipment.modificationSockets: expected at most 8 sockets')
                else:
                    socket_ids = set()
                    for socket in sockets:
                        if not isinstance(socket, dict) or set(socket) != {'id','label','type'} or not isinstance(socket.get('id'), str) or not ID.fullmatch(socket['id']) or not isinstance(socket.get('label'), str) or not 1 <= len(socket['label']) <= 80 or socket.get('type') not in ('implant','armour_plate','armour_lining','armour_motor','armour_utility'):
                            errors.append(f'{w}.equipment: invalid socket')
                        elif socket['id'] in socket_ids: errors.append(f'{w}.equipment: duplicate socket ID')
                        else: socket_ids.add(socket['id'])
                    if equipment['kind'] == 'implant' and (len(sockets) != 3 or any(not isinstance(v, dict) or v.get('type') != 'implant' for v in sockets)):
                        errors.append(f'{w}.equipment: implants require exactly three augmentation sockets')
                modifiers = equipment['modifiers']
                if not isinstance(modifiers, list) or len(modifiers) > 32: errors.append(f'{w}.equipment.modifiers: expected at most 32 effects')
                else:
                    for modifier in modifiers:
                        if not isinstance(modifier, dict) or set(modifier) != {'stat','flat','percent'} or not isinstance(modifier.get('stat'), str) or not re.fullmatch(r'[a-z][A-Za-z0-9]{1,63}', modifier['stat']):
                            errors.append(f'{w}.equipment: invalid modifier'); continue
                        number(modifier['flat'], w+'.equipment.flat', -100000, 100000)
                        number(modifier['percent'], w+'.equipment.percent', -1, 100)
        for field in ('category','subtype','rarity'):
            if not isinstance(x.get(field), str) or len(x[field]) > 80: errors.append(f'{w}.{field}: invalid text')
        number(x.get('tier'), w+'.tier', 0, 100, True)
        number(x.get('weightKg'), w+'.weightKg', 0, 10000)
        number(x.get('stack'), w+'.stack', 1, 100000, True)
        tags = x.get('tags')
        if not isinstance(tags, list) or len(tags) > 32 or any(not isinstance(t,str) or not TAG.fullmatch(t) for t in tags) or (isinstance(tags,list) and len(tags)!=len(set(t for t in tags if isinstance(t,str)))):
            errors.append(f'{w}.tags: invalid/duplicate tag')
        stats = x.get('stats')
        if not isinstance(stats,dict) or len(stats)>32: errors.append(f'{w}.stats: expected object')
        else:
            for key, value in stats.items():
                if not TAG.fullmatch(key): errors.append(f'{w}.stats: invalid property name')
                number(value,w+'.stats.'+key,-100000,100000)
    for i, r in enumerate(data['recipes']):
        if not isinstance(r, dict): continue
        w = f'recipes[{i}]'
        if set(r) != {'id','name','station','seconds','inputs','outputs'}: errors.append(f'{w}: unexpected or missing fields')
        if not isinstance(r.get('station'),str) or not ID.fullmatch(r['station']): errors.append(f'{w}: invalid station ID')
        number(r.get('seconds'),w+'.seconds',0,36000)
        for field in ('inputs','outputs'):
            rows = r.get(field)
            if not isinstance(rows,list) or not 1 <= len(rows) <= 32: errors.append(f'{w}.{field}: expected 1..32 entries'); continue
            for j, entry in enumerate(rows):
                loc = f'{w}.{field}[{j}]'
                if not isinstance(entry,dict): errors.append(f'{loc}: expected object'); continue
                number(entry.get('quantity'),loc+'.quantity',1,100000,True)
                if field == 'inputs':
                    if set(entry) != {'kind','ref'} | {'quantity'} or entry.get('kind') not in ('item','tag'): errors.append(f'{loc}: expected item/tag input'); continue
                    ref = entry.get('ref')
                    if entry['kind']=='item' and ref not in items: errors.append(f'{loc}: unknown item {ref}')
                    if entry['kind']=='tag':
                        if not isinstance(ref,str) or not TAG.fullmatch(ref): errors.append(f'{loc}: invalid tag')
                        elif not any(ref in x.get('tags',[]) for x in items.values()): errors.append(f'{loc}: impossible tag {ref}')
                else:
                    if set(entry) != {'itemId','quantity'} or entry.get('itemId') not in items: errors.append(f'{loc}: unknown output item')
        # Recipe dependency edges, including tag matches. These can reveal circular crafting.
        for inp in r.get('inputs',[]) if isinstance(r.get('inputs'),list) else []:
            if not isinstance(inp,dict): continue
            sources = [inp.get('ref')] if inp.get('kind')=='item' else [k for k,v in items.items() if isinstance(v.get('tags'),list) and inp.get('ref') in v['tags']]
            for out in r.get('outputs',[]) if isinstance(r.get('outputs'),list) else []:
                if isinstance(out,dict) and out.get('itemId') in graph:
                    graph[out['itemId']].update(s for s in sources if s in items)
    for i, enemy in enumerate(data['enemies']):
        if not isinstance(enemy,dict): continue
        w=f'enemies[{i}]'
        if set(enemy) != {'id','name','loot'}: errors.append(f'{w}: unexpected or missing fields')
        loot=enemy.get('loot')
        if not isinstance(loot,list) or len(loot)>32: errors.append(f'{w}.loot: expected <=32 entries'); continue
        for j, drop in enumerate(loot):
            loc=f'{w}.loot[{j}]'
            if not isinstance(drop,dict): errors.append(f'{loc}: expected object'); continue
            if set(drop) != {'itemId','min','max','chance'} or drop.get('itemId') not in items: errors.append(f'{loc}: unknown item/fields')
            number(drop.get('min'),loc+'.min',0,100000,True)
            number(drop.get('max'),loc+'.max',0,100000,True)
            number(drop.get('chance'),loc+'.chance',0,100)
            if type(drop.get('min')) is int and type(drop.get('max')) is int and drop['min']>drop['max']: errors.append(f'{loc}: min exceeds max')
    return errors[:100]


def diagnostics(data):
    items={x['id']:x for x in data['items']}; used=set(); produced=set(); seeded=set()
    for e in data['enemies']:
        seeded.update(d['itemId'] for d in e['loot'] if d['chance']>0 and d['max']>0)
    edges=[]
    for r in data['recipes']:
        outputs=[d['itemId'] for d in r['outputs']]; produced.update(outputs)
        for inp in r['inputs']:
            sources=[inp['ref']] if inp['kind']=='item' else [k for k,x in items.items() if inp['ref'] in x['tags']]
            used.update(sources)
            if len(edges) + len(sources) * len(outputs) > 20000:
                raise ValueError('Draft graph exceeds 20000 diagnostic edges')
            edges.extend(dict(source=s,target=o,recipe=r['id'],kind='consumes → produces',sourceType='draft') for s in sources for o in outputs)
    available=set(seeded)
    for _ in range(len(items)+1):
        old=len(available)
        available_tags={tag for k in available for tag in items[k]['tags']}
        for r in data['recipes']:
            if all((v['ref'] in available if v['kind']=='item' else v['ref'] in available_tags) for v in r['inputs']):
                for o in r['outputs']:
                    if o['itemId'] not in available:
                        available.add(o['itemId'])
                        available_tags.update(items[o['itemId']]['tags'])
        if len(available)==old: break
    adj={k:[] for k in items}
    for e in edges: adj[e['source']].append(e['target'])
    seen=set(); active=set(); cycles=set()
    for v in items:
        if v in seen: continue
        seen.add(v); active.add(v)
        stack=[(v, iter(adj[v]))]
        while stack:
            node, children=stack[-1]
            child=next(children, None)
            if child is None:
                active.remove(node); stack.pop()
            elif child in active:
                cycles.add(child)
            elif child not in seen:
                seen.add(child); active.add(child)
                stack.append((child, iter(adj[child])))
    return dict(source='draft', edges=edges, orphans=sorted(set(items)-used-produced-seeded), impossible=sorted(produced-available), circular=sorted(cycles), seeded=sorted(seeded))

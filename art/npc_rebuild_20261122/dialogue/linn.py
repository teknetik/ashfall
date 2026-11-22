#!/usr/bin/env python3
"""Linn's dialogue, 22 Nov 2026 (Carl: "its very borning. it should introduce so lore").

This file is the source of her words. It rewrites the nodes and entries of Data/npc_linn.asset, idempotently, and keeps
what other systems read: the node ids greeting, hill, housing and housing_leased, the choice ids tree, housing and lease,
the lease_home action, the housing requirement and its flag. The first greeting choice always leads on into dialogue
(the city loop check presses it).

Canon is lore.md. Why Tir was cut off stays unknown: Linn gives the three rumours and says that nobody knows.
A node shows at most three choices (GameSession.MaxChoices).

  linn.py            write the dialogue
  linn.py --bind     also bind NpcVoices/npc_linn-<node>.wav, creating the .meta of a new take
"""
import json, re, sys, uuid
from pathlib import Path

A = Path(__file__).resolve().parents[3] / 'unity/AthenHill/Assets/AthenHill'
ASSET = A / 'Data/npc_linn.asset'
VOICE = A / 'Audio/ElevenLabs/NpcVoices'

HOUSING = 'primer, !flag:home_leased'
MET = 'linn_met'

def c(id, label, next='', action='', requires='', flag=''):
    return dict(id=id, label=label, next=next, action=action, requires=requires, setFlag=flag)

def leave(label='Another time, Linn.'):
    return c('leave', label, action='close', flag=MET)

stay = c('housing', 'Is there anywhere in Ward I could stay?', 'housing', requires=HOUSING, flag='home_asked')
back = c('back', 'Let me ask you something else.', 'again')

NODES = [
 ('greeting', 'Elder of the hill',
  "Sit, before the sun finishes you. New people always stare at the walls. Look at the tree instead. "
  "Everything Ward has ever bled for is down under those roots.",
  [c('tree', "What's under the tree?", 'hill', flag=MET), stay, leave()]),

 ('again', 'Elder of the hill',
  "Still breathing? Good. Sit. Old women and old cities both like to be asked about themselves.",
  [c('tree', 'Tell me about Ward.', 'hill'), stay, leave('Just passing, Linn.')]),

 ('hill', 'The oasis',
  "Water. The only sure well for hundreds of kilometres. The company built here for the ore, back when Tir was a line "
  "in somebody's accounts. They dug it, shaped it, shipped it off-world. Then one season, the ships didn't come.",
  [c('fall', 'What happened when they stopped?', 'fall'), c('wardens', 'Who guards the water now?', 'wardens'), back]),

 ('fall', 'The Fall',
  "Nobody told the machines. Some kept digging for masters long dead. Others decided we were in the way, "
  "or that we were ore. The cities went dark, one, then the next, then all of them. That's what we call the Fall.",
  [c('silence', 'Why did no one come back for you?', 'silence'), c('rebuild', 'How did Ward survive?', 'rebuild'), back]),

 ('silence', 'The silence',
  "They forgot us. They fenced us off for fear of the machines. Or they had it worse. I've heard all three sworn as "
  "truth, and never by anyone who'd know. The women of my family set out a cup for the supply pilot. "
  "It has been dry for centuries, and I still wash it.",
  [c('rebuild', 'And Ward carried on without them.', 'rebuild'), back]),

 ('rebuild', 'The Great Rebuild',
  "Out of spite, mostly. One greenhouse, one nanofab, a few machines that stayed loyal. Then we woke the Quantum Tubes. "
  "Goods pulled to dust here and knitted whole at the far end. After that, dead nodes began waking on their own. "
  "Ask an engineer why, and watch them change the subject.",
  [c('karaveen', 'What carried goods before the Tubes?', 'karaveen'), c('wardens', 'Who held the walls?', 'wardens'), back]),

 ('karaveen', 'The Karaveen',
  "The Karaveen. When the cities fell they took to the sand, and for a lifetime they were the only thread between one "
  "well and the next. The Tubes made them needless. Still they go. There are people out there no Tube will ever reach, "
  "and the Karaveen know their children's names.",
  [c('berms', "What's out there?", 'berms'), back]),

 ('wardens', 'The Wardens',
  "The Wardens. They began as neighbours taking turns on the wall. Now some have more lattice in them than bone, "
  "and scraps of old machine minds to steady the gun. I've washed three of them for burial. "
  "They are the wall that has never been allowed to fall.",
  [c('berms', 'What are they holding back?', 'berms'), c('rebuild', 'How did it all start again?', 'rebuild'), back]),

 ('berms', 'The Outer Berms',
  "The Outer Berms. Factories to the horizon, once. Now it's their bones, and whatever still walks about inside them. "
  "There are secrets under that scrap. Few go looking, and fewer come home. So don't go out in just a shirt. "
  "Mira sells a vest and boots. Better plate, you build.",
  [c('ready', "I'll remember that.", action='close', flag=MET), back]),

 ('housing', 'The housing roll',
  "There's a red container on the south wall, behind the Nanofab yard. The family left with a Karaveen caravan and made "
  "the bunk before they went. That's how you know they won't be back. Forty credits, and I write your name on the roll. "
  "In Ward that's worth more than the key. It means somebody counts you.",
  [c('lease', "I'll take the lease (40 credits).", 'housing_leased', action='lease_home'),
   c('later', "Not yet. I'll come back.", action='close', flag=MET)]),

 ('housing_leased', 'The housing roll',
  "There. Written. The door knows you now, and so does the city. If some night you don't come home, "
  "someone will notice. Out here, that's most of what a home is.",
  [c('leave', 'Thank you, Linn.', action='close', flag=MET)]),
]
ENTRIES = [('again', 'flag:' + MET)]


def q(v):
    return json.dumps(v, ensure_ascii=True) if v else ''


def line(key, v, indent):
    return (' ' * indent + key + ': ' + q(v)).rstrip() + '\n' if v else ' ' * indent + key + ': \n'


def voice_ref(id, bind):
    wav = VOICE / f'npc_linn-{id}.wav'; meta = Path(str(wav) + '.meta')
    if bind and wav.exists() and not meta.exists():
        t = (VOICE / 'npc_linn-greeting.wav.meta').read_text()
        meta.write_text(re.sub(r'(?m)^guid: \w+', 'guid: ' + uuid.uuid4().hex, t, count=1))
    if not (wav.exists() and meta.exists()):
        return '{fileID: 0}'
    g = re.search(r'(?m)^guid: (\w+)', meta.read_text()).group(1)
    return '{fileID: 8300000, guid: %s, type: 3}' % g


def main():
    bind = '--bind' in sys.argv
    ids = {n[0] for n in NODES}
    assert len(ids) == len(NODES)
    for id, _, _, choices in NODES:
        assert len(choices) <= 3, id
        for x in choices:
            assert x['action'] == 'close' or x['next'] in ids, (id, x)
    s = ASSET.read_text()
    out = '  entries:\n' + ''.join(f'  - node: {n}\n    requires: {q(r)}\n' for n, r in ENTRIES) + '  nodes:\n'
    for id, title, text, choices in NODES:
        out += f'  - id: {id}\n' + line('title', title, 4) + line('text', text, 4) + f'    voice: {voice_ref(id, bind)}\n    choices:\n'
        for x in choices:
            out += f"    - id: {x['id']}\n" + ''.join(line(k, x[k], 6) for k in ('label', 'next', 'action', 'requires', 'setFlag'))
    a, b = s.index('  entries:'), s.index('  shop:')
    s = s[:a] + out + s[b:]
    s = re.sub(r'(?m)^  role: .*$', '  role: Elder of the hill', s)
    ASSET.write_text(s)
    for id, _, text, _ in NODES:
        print(f'{id:15} {len(text):4} chars')
    print('total', sum(len(n[2]) for n in NODES))


if __name__ == '__main__':
    main()

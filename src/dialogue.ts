import type { NamedNPCId } from './npc';

export type DialogueAction = 'shop' | 'close';
export type DialogueChoice = Readonly<{ id: string; label: string } & (
  { next: string; action?: never } | { action: DialogueAction; next?: never }
)>;
export interface DialogueNode {
  readonly speaker: string;
  readonly title: string;
  readonly text: string;
  readonly choices: readonly [DialogueChoice, DialogueChoice];
}

function node(speaker: string, title: string, text: string, choices: [DialogueChoice, DialogueChoice]): DialogueNode {
  const frozenChoices: readonly [DialogueChoice, DialogueChoice] = Object.freeze([
    Object.freeze(choices[0]), Object.freeze(choices[1]),
  ]);
  return Object.freeze({ speaker, title, text, choices: frozenChoices });
}

const DIALOGUES: Readonly<Record<NamedNPCId, Readonly<Record<string, DialogueNode>>>> = Object.freeze({
  npc_mira: Object.freeze({
    greeting: node('Mira', 'Basic General',
      'Welcome to Basic General. Fresh seals on the flasks, checked packs in the medkits. I can buy that scrap coil if you need a few credits.', [
        { id: 'browse', label: 'Show me your stock.', action: 'shop' },
        { id: 'leave', label: 'Just looking. Thanks, Mira.', action: 'close' },
      ]),
  }),
  npc_torr: Object.freeze({
    greeting: node('Torr', 'Local fixer',
      'The city looks quiet from the hill. Down here, every cracked terminal has someone waiting on a spare part.', [
        { id: 'terminals', label: 'What is this slab used for?', next: 'slab' },
        { id: 'leave', label: 'I will leave you to it.', action: 'close' },
      ]),
    slab: node('Torr', 'Local fixer',
      'It used to match shifts with maintenance crews. Today we leave notes for each other. Ask around the hill before you trust a blank screen.', [
        { id: 'back', label: 'About the city...', next: 'greeting' },
        { id: 'leave', label: 'I will remember that.', action: 'close' },
      ]),
  }),
  npc_vex: Object.freeze({
    greeting: node('Vex', 'Free Column guard',
      'Keep the passage clear and watch for the carts. Free Column rules are simple: everyone gets through, and everyone helps keep the gate standing.', [
        { id: 'gate', label: 'Has this gate always been here?', next: 'gate' },
        { id: 'leave', label: 'Understood. Safe watch.', action: 'close' },
      ]),
    gate: node('Vex', 'Free Column guard',
      'The stone is older than the towers. Look closely and you can see three generations of repairs. We keep the old blocks because they still do the job.', [
        { id: 'back', label: 'About those gate rules...', next: 'greeting' },
        { id: 'leave', label: 'I will keep the path clear.', action: 'close' },
      ]),
  }),
  npc_linn: Object.freeze({
    greeting: node('Linn', 'Hill regular',
      'Looking for someone? Try the shade. Sooner or later everyone comes up here, even the people who swear they are too busy.', [
        { id: 'tree', label: 'Why does everyone meet here?', next: 'hill' },
        { id: 'leave', label: 'I will stay for a moment.', action: 'close' },
      ]),
    hill: node('Linn', 'Hill regular',
      'You can see the gate, hear the market, and get out of the dust. No terminal needs to explain that. If we get separated, meet me on the hill.', [
        { id: 'back', label: 'Who comes up here?', next: 'greeting' },
        { id: 'leave', label: 'On the hill. Got it.', action: 'close' },
      ]),
  }),
});

/** Unknown nodes fail explicitly instead of selecting an unrelated conversation. */
export function getDialogue(npcId: NamedNPCId, nodeId = 'greeting'): DialogueNode {
  if (!Object.hasOwn(DIALOGUES, npcId)) throw new Error(`Unknown dialogue NPC: ${String(npcId)}.`);
  const dialogue = DIALOGUES[npcId];
  if (!Object.hasOwn(dialogue, nodeId)) throw new Error(`Unknown dialogue node for ${npcId}: ${String(nodeId)}.`);
  return dialogue[nodeId];
}

# Meshy animation reference

## User-supplied animation list — 2 October 2026

Carl supplied this list of animations available to him in Meshy for future
character and animation work on Ashfall / Ward.

[Full animation list](../meshy/animation-reference/2026-10-02-animation-names.txt)
— 631 entries, 587 distinct names. The original text is preserved verbatim,
including order, spelling, punctuation and 44 repeated names. Source: the
user's `Pasted text.txt` attachment supplied on 2 October 2026.

Use the list when choosing candidate animations for the player, talking NPCs
and ambient actors. It records available choices reported by the user; it does
not indicate that those clips have been generated, imported or tested in Unity.

## Animation IDs and previews

The existing [Meshy library snapshot](../meshy/character-feel-20260927/animation-library.json)
contains 678 records with `action_id`, `name`, `key`, `category`, `sub_category`
and `preview_url`. It is a separate earlier reference, not replaced by this list.

Look up names there when preparing an animation request, and confirm the selected
variant and current ID before generation. Line numbers in the supplied list are
not animation IDs. Repeated display names may identify different variants: the
snapshot has `Carry Heavy Object Walk` as both action 551
(`Carry_Heavy_Object_Walk`) and action 611 (`Carry_Heavy_Object_Walk_inplace`).

For integration, follow the [production guide](../AGENTS.md),
[player source record](../unity/MESHY_PLAYER.md) and
[Unity editing workflow](../unity/EDITING.md). Preserve source clips and gameplay
roots, then review the selected motion on the intended rig in native Unity.

# Carl's requests — 27 Sep 2026, ~11:40 BST (second pass brief)

Context: read `HANDOFF-NEXT.md` (this folder) first, then `unity/evidence/character-feel/20260927/README.md`.
Nothing is committed; keep all uncommitted work. Paths under `Scripts/`, `Editor/`, `Art/` are relative to
`unity/AthenHill/Assets/AthenHill/`.

Reference images (saved in this folder):
- `composer_2026-09-27_11-37-41-722_ca07f5.png` — in-game first-person pistol hold (range, Outer Berms). Better than
  before but the hands still read as garbled: faceted, oversized, fingers interpenetrating, grip unclear.
- `composer_2026-09-27_11-38-54-798_da029d.png` — real photo target: a two-handed grip seen from behind, with the
  support hand wrapped around the firing hand, thumbs forward along the frame and the slide centred and level.

## Requests (Carl's words paraphrased; priority order is mine)

1. **Player run animation too fast.** Run *speed* is fine; the legs "scamper like a rat". Slow the run clip's
   playback by about 15%. Keep movement speed unchanged, so check the stride/foot slide after the change (lengthen the
   stride or accept the result, and record which).
2. **Warden Ossa's feet are buried in the sand.** Raise Ossa's root or ground-snap it so the feet sit on the terrain.
   Check the other Wardens too.
3. **Tree in the middle of the road** just past the target shooting range, on the road to the robots (the service
   road to the depot/worker droids). Move or remove it so the road is clear, and check the colliders and route.
4. **Karaveen truck too big.** It can't fit through the gate and is too large overall. Scale it down *uniformly* to a
   sensible size, roughly a real heavy cargo truck at about 2.5 m wide and 3.5–4 m tall, and make sure it fits the
   gate opening with clearance. Don't stretch the axes independently.
5. **Time of day.** Start the game later in the afternoon, just as it's getting dark: low golden sun heading into
   dusk. Adjust the sun angle and colour, sky, ambient light and exposure coherently. Check that the UI stays readable
   and that shade isn't crushed. The accepted dust-bowl atmosphere pass is the baseline.
6. **First-person pistol grip.** Rework it toward the photo reference: a proper two-handed cup grip with fingers not
   interpenetrating and correct hand size. This matches HANDOFF-NEXT item 4 (a dedicated FP arms mesh), so use
   Meshy/Blender if needed. Note that `art/character_feel_20260927/fp_arms/` already exists; inspect it first.
7. **More people.** The whole place needs more life.
   - Use Meshy (preapproved credits) to create several new NPC characters, lore-appropriate for Ward colonists,
     Karaveen traders and workers (see `lore.md`), then rig and animate them.
   - **Street vendors / market NPCs** stand at stalls (e.g. the Karaveen caravan market) and are **tradable**: reuse
     the existing ShopModel/CityCatalog trading flow with atomic inventory and credit changes.
   - **All other new NPCs only walk around** on routes (AmbientWalker-style), with no dialogue.
   - Keep the existing four talking NPCs, the walkers and their routes intact. Measure the frame-time cost.

Feedback, not work: the new gun sounds are "much nicer", so keep them.

## Standing constraints
- Follow `AGENTS.md`: work in the saved scene and prefabs, apply narrow edits, rebuild render chunks, and verify in a
  native Linux build with the Editor closed.
- Run the Edit Mode tests and the existing native checks: `check_character_feel.py`, `check_checkpoint.py` and
  `check_depot.py`.
- Record dated evidence under `unity/evidence/`.
- Carl is lenient on frame rate for now, but record it.
- Do not commit.

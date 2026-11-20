# Carl's playtest notes (20 November 2026)

Notes Carl sent while playing. All six were fixed on 20 November ("fix those for now", 07:41) in
`Builds/batch-p2-notes` (08:47; record: README.md, section "Playtest fixes, 20 November morning"). His words are
quoted; the "reading" lines are the agent's interpretation and may be wrong.

Build played: not stated (the phase 2 build is `Builds/batch-p2-final`).

## Interface

1. **"Implants need a eye slot"**
   Reading: the implants panel has HEAD, ARMS, CHEST, WRIST, WAIST, HAND, LEGS and FEET; add an EYE slot.
   His screenshot shows "Neural Targeting ..." sitting in HEAD.
   Done: EYE slot `implant_eye` added after HEAD (`LoadoutFixPass20261120`, `art/loadout_fix_20261120/README.md`); it is
   empty, because no eye implant exists and Neural Targeting (a neural "targeting lattice") stays in HEAD; old saves
   load with the eye empty. Seen on `batch-p2-notes`; loadout check 72/72. Open: no item fits the slot yet.
2. **"Implant slots point to the wrong places."**
   Reading: the leader lines from the slot boxes end on the wrong body parts of the X-ray figure. In his screenshot
   ARMS ends on the upper chest, CHEST on the lower ribs, WRIST on the pelvis, WAIST on the thigh, HAND on the knee,
   LEGS on the shin.
   Done: the dots were never placed against the figure; each body part now has an anchor measured on the figure image
   and boxes sit beside the figure (`Scripts/AnatomyLayout.cs`, same record). Seen on `batch-p2-notes` at 1920x1080:
   every leader ends on the part its slot names; loadout check 72/72, Edit Mode 428/428. Open: not seen on a real
   3840x2160 screen.
3. **"Hot bar titles dont go away. I also expect to be able to rearrange this bar does not look possible."**
   Reading: (a) item name tooltips ("Nano Recharge Cell", "Medkit") stay on screen after the pointer leaves, and
   stack up; one is still showing over the armour panel in his third screenshot. (b) He expects to drag a hotbar cell
   onto another cell to reorder; today items can only be dragged in from the pack or cleared.
   Done: (a) they were drag labels left by the strip's own drag code, not tooltips; the strip now uses the pack's drag
   (one label at most, always removed). (b) Drag a cell 3–0 onto another to move or swap, or focus a cell and press a
   number; 1 and 2 stay fixed to the weapons; the order is saved. Same record. Seen on `batch-p2-ui3`: one label during
   a drag, the medkit moved from 3 to 5, the order kept after a restart; loadout check 72/72 on `batch-p2-notes`. Open:
   a release outside the game window (covered by a 100 ms watchdog) not exercised.
4. **"Armor section. same deal with where the labels point. Random word "head" at the bottom of the page."**
   Reading: (a) the armour panel's leader lines are wrong in the same way (ARMS on the sternum, PACK on the chest,
   HANDS on the pelvis, LEGS on the knee). (b) A stray "Head" label is printed at the bottom left of both the
   implants and the armour panels (probably the selected slot's name with nothing under it).
   Done: (a) fixed with note 2 (PACK now ends on the shoulder). (b) It was the selection label; it is hidden on both
   body-map pages. Same record. Seen on `batch-p2-notes`: no stray label under either figure. Open: at 4:3 the armour
   page's boxes go compact and long names wrap.

## Audio

5. **"Linns voice does not match, should be more older and rough"**
   Reading: re-voice Linn (the elder on the hill) with an older, rougher voice: her dialogue lines and her bark
   lines. This is the first feedback on any voice.
   Done: all 13 of Linn's lines (4 dialogue nodes, 9 barks) re-voiced in Seer Morganna, Carl's choice of three
   candidates ("B is the best I think"); the housing offer and the reply after the lease had no audio before and are
   now voiced (`LinnVoicePass20261120`, `art/linn_voice_20261120/README.md`). Native check 25/25 on `batch-p2-notes`.
   Open: Carl has heard 2 of the 13 takes; "Berms" in "You came back from the Berms" transcribes as "bums" or "bombs",
   "Karaveen" as "Caravene"; the greeting is slow (11.5 s), the housing offer 28.2 s.

## World

6. **"Barrels on the floor by the waste gate, the broken ones on the floor need to be able to be walked over or need
   to go"**
   Reading: "waste gate" = West Gate (the gate by the market out to the Berms). The fallen or broken barrels lying on
   the ground there block walking: remove their colliders so the player walks over them, or remove the barrels.
   To confirm: which gate, if not the West Gate.
   Done: read as the West Gate; the broken set is at the Karaveen caravan overflow by the truck, 14 m inside it (the
   spot Carl raised on 3 October), where the 3 Oct box stood over the staves. Colliders now hold only the whole barrels
   there and at the Rations stall's set; staves, lids and halves (at most 0.39 m) are walked over; nothing removed
   (`GateBarrelsPass20261120`, `art/gate_barrels_20261120/README.md`). Seen on `batch-p2-ui2`: the colonist standing
   among the staves; check 59/59 on `batch-p2-notes`. Open: his feet passing through the 0.3 m barrel half in motion.

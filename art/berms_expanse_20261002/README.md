# Outer Berms expansion (2 October 2026)

Carl: "We need to expand the outer berms, push back the mountains if required. Even as a tutorial it's quite small with
like 3-4 robots to kill. Spread [the loot] and enemies out a little. Make them more challenging. Use Meshy to create 2 more
enemies a bit further out that use ranged weapons for more of a challenge." Then: "it needs to be quite big and spread
out like 500m".

The Outer Berms grew from a 44 x 102 m pocket (4,600 m²) to a desert bowl about **495 x 425 m (150,000 m²)** west of the
West Gate. The western mountains were pushed back and rebuilt around it; twelve sites with their own dressing, encounters
and salvage spread across it; melee droids are tougher and fight as packs; two new **ranged** droids (Meshy) hold the
outer sites; a Warden waystation in the middle becomes the respawn point once found.

## Pipeline (run order)

All Python runs through the memory-capped wrappers (`~/.local/state/ward-programme/heavy.sh`); `work/rebuild.sh <tag>`
runs steps 1–4 in order (~8 min).

1. `expanse_heightfield.py` → `work/heightfield.npz`, `heightfield.json`, and the derived `playable` polygon written back
   into `footprint.json`. A 2049 x 2049 grid at 1 m (X −1088…960, Z −1024…1024), derived from
   `art/basin_mountains_20261001/basin_heightfield.py` (same landform family, stream-power incision, strata terraces,
   droplet erosion, talus, rock detail, light bake):
   - **Bowl**: `footprint.json` `bowl` is a hand-drawn outline of the new mountain foot, warped by noise into bays and
     promontories. New mountains grow outward from it with the original tableland profile (front escarpment, crest ring,
     distant ring) with noise-varied amplitudes; west of x −220 they replace the original ring, between x −220 and −90
     they merge with it, and east of the gate nothing changes. (A first attempt pushed the old ring radially outward; it
     stretched every ridge into a circular arc and was dropped; `work/expanse_heightfield_v1_small.py` is the earlier
     140 m version.)
   - **Floor**: inside the playable polygon a rolling floor (macro swells, dunes, rising ~7 m toward the western fans),
     two meandering dry washes and six lobed sandstone outcrops (relay knoll, split butte, north mesa, fan rocks, wash
     pillar, south ridge) that erosion then cuts. The mountain foot may only rise inside the polygon's 16 m edge ramp.
   - **Depot rise**: the original Berms ground climbs 7–11 m on its south-west edge (the depot conveyor stands on it); its
     edge heights are carried outward into a spur that falls off over ~20 m.
   - **Lock**: inside the original Berms footprint (x −104…−60, z −54…48) the surface is the old basin exactly (0.6 mm), so
     the old `Berms ground` mesh and everything on it is untouched.
2. `layout.py` → `sites.json`, `layout-check.json`, `work/layout.png`: the twelve sites as data (kit props with offsets,
   encounter spawns, salvage nodes with prompts and loot tables, landmark ids), the Warden trail routes and the tutorial
   changes; validated against the terrain (inside the floor, slope under each footprint, walker spawns nudged off steep
   ground, site spacing).
3. `scatter.py` → `scatter.json`, `work/scatter.png`: 835 rocks, boulders, stones, scrub and dead wood (Poly Haven kit
   prefabs) by Poisson-disc sampling with density from talus, wash banks and the mountain foot; clear of sites and routes.
4. `expanse_mesh.py --theta 0.012` → `Art/BermsExpanse/BasinExpanse.glb` (84 spatial chunks, 323k triangles; one RTIN, chunks
   share every border vertex; a first 8-sector x 2-ring split drew whole 550 m wedges into every shadow cascade) and `Art/BermsExpanse/BermsExpanseGround.glb` (54 tiles of 64 m, LOD0 2.5 cm error 132k
   triangles, LOD1 12 cm 67k; tile borders and the old footprint edge fully refined so tiles join at any LOD mix and meet
   the old ground mesh's 1 m edge exactly); `mesh.json`. Written straight from numpy (`glb_write.py`), no Blender step.
5. Unity, batch (`~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.BermsExpansePass.RunBatch -nographics
   -quit --steps …`): `survey`, `prefabs` (kit footprints → `prefabs.json`), `loot`, `droids`, `install`, `verify`,
   `capture:<dir>:cam+cam` (graphics, ≤ 6 cameras), `abbuild:on|off`. `install` is re-runnable (it removes what it made
   before and re-applies its edits); see unity/EDITING.md "Outer Berms expansion".
6. Native: `run/native_check.sh <out>` (`unity/tools/check_berms_expanse.py`), `run/editmode.sh <out>`.

## Files

`footprint.json` (grid, old footprint, bowl, floor/wash/outcrop parameters, derived playable polygon), `sites.json`,
`scatter.json`, `review_cameras.json` (`cam_bx_*`, heights above ground), `heightfield.json`, `mesh.json`,
`layout-check.json`, `survey.json` (the scene before the pass), `prefabs.json`; scripts `expanse_heightfield.py`,
`layout.py`, `scatter.py`, `expanse_mesh.py`, `glb_write.py`, `plot_area.py`, `plot_zoom.py`, `run/*.sh`.
Git-ignored: `work/` (heightfields, plots).

## Sources and licences

Terrain is procedural and original (this folder and art/basin_mountains_20261001). Props are existing kit prefabs (Poly Haven
CC0 scans, Blender-authored kits, earlier Meshy pieces; see their records). New Meshy assets: the ranged droids
(meshy/ranged-enemies-20261002) and the three hero landmarks (meshy/berms-landmarks-20261002). Sound: six ElevenLabs
one-shots added to `unity/tools/generate_berms_combat_audio.py` (gunner-aim, gunner-fire, lancer-charge, lancer-fire,
bolt-impact, bolt-flyby).

## Revision, 2 October 2026 14:00 (pistol/rifle session)

Carl playtested the expansion build and did not see the droids that used to meet him just outside the gate: this pass
had moved the primer's first contact 70 m west past the depot rise (`layout.py` TUTORIAL first_contact), so after the
plates nothing was in sight and his save sat at FirstContact. The **First contact · service road** encounter is back on
the service road beside the gate: root (-83, -0.9, -13), the second drone at (-89, -0.8, -6), 30 m from the gate marker
(`unity/evidence/rifle-armour/20261002/README.md`). `BermsTutorial` now gives the HUD marker a target for the
FirstContact (nearest live drone, "SCRAP DRONE") and Depot ("MACHINE DEPOT") steps. `sites.json` / `layout.py` still
record the pass's own positions; the saved scene is the authority. `BermsExpanseTests` asserts the new placement.

# Hero base: integration progress (started 20 Nov 2026, after Carl's "Yes, go ahead")

Route chosen: keep the Meshy SmartRig natively (so Meshy library clips play without rest-pose matching) but shape the
file to the game's contract: root `Armature`, 54 joints (24 body + 30 fingers), fingers renamed to the MPFB names
`{index,middle,ring,pinky,thumb}_{01,02,03}_{l,r}` and re-rolled so they curl about local X, legacy clips `idle`,
`walk`, `run` inside colonist.glb, one material `PlayerSkin`, at most 90k triangles. Height is normalised to 1.80 m by
MainCharacterInstall (the project's actor standard); the file stays at Meshy's 1.88.

Surveys (20 Nov): player install pipeline and bone-name dependencies; key facts are in the session and summarised in
README once done.

| Step | State |
| --- | --- |
| Face repaint (3 views, Meshy nano-banana-pro, 27 credits) projected onto the texture; skin and hair graded to match | done: `face/` (`face_views.py`, `face_project.py`), check `face/check_v1/check_sheet.jpg` |
| Texture set: hem tag painted out, normal map flattened on the face (75 %) and skin (35 %), skin a little smoother | done: `build/finish_textures.py` -> `build/tex/` |
| Player's 12 source clips + idle 248 fetched natively on the new rig (44 Meshy credits incl. rig) | done: `rig/*.glb` |
| Runtime model: 80k triangles (head and hands protected), 54 bones, fingers renamed and re-rolled (curl agreement with the old rig >= 0.915 on all 30 joints), left wrist joint moved 20 mm to the real wrist, hand weights smoothed, idle/walk/run embedded | done: `build/build_hero.py` -> `build/hero.blend`, `build/out/colonist.glb`; checks `build/check_hero.py`, `build/renders/` |
| First-person arms | done: `build/out/TS_FPArms.glb` (21.8k triangles, no textures of its own) |
| Slim Source/Player clips (7.4 MB for 12, was 43 MB) | done: `build/slim_clip.py` -> `build/out/source/` |
| Armour re-fit (7 pieces) | running: background agent, `armour/` |
| Unity pass and driver | written, not yet in the project: `unity/HeroBasePass20261120.cs`, `unity/apply.py`, `unity/install.sh` |
| Unity: install chain, tests, native checks | todo; the crafting session has released the Unity lock; window to be agreed |
| Docs (AGENTS.md row, EDITING.md, README) | todo |

Measured for the Unity constants (file scale; the game scales by 0.9575): finger radius about 13.5 mm, thumb 15-17 mm
(`build/fingers.json`); phalanges 23-24 mm; wrist to middle knuckle 135 mm.

Notes
- fal ran out of credits after the Rodin run (upload refused, 20 Nov ~10:25). Face repaint went through Meshy instead.
- Another session ("Game crafting system depth") is building and running native checks; messaged 20 Nov ~10:45.

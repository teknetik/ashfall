# player_face_20261003 — progress log (3 Oct 2026)

1. Read COMMON.md / AGENTS.md. Inspected the MPFB chain (`mpfb_build.py`, `finish_body.py`), the NPC pipeline and
   captures. Found: hair/beard/brow/lash cards exported as glTF alpha BLEND (solid slabs in Unity); skin is the 2k
   MakeHuman diffuse with no normal/roughness; eye iris strongly red.
2. `inspect_skin.py`: UV layout (`renders/uv_layout_human.png`): one big head island, ears, scalp, neck, hands; lots of
   empty UV space. `prep_meshy.py`: skin-only GLB for Meshy with eyes packed into an empty corner; clay renders.
3. Codex concept paint-over of the clay head (`concept/face_concept_v1.png`), three Meshy retextures (text, single image,
   multi-view; 30 credits). Rendered with the NPC inspection light next to Torr: multi-view chosen.
4. Painted hair alone read flat in profile → alpha-clipped shells on the painted hair (`shells.py`). v1 random strands looked
   like a screen and covered the eyes; v2 strands follow the painted strokes, eye zone excluded.
5. `finish_body.py`: new skin, shells, MASK alpha, COLOR_0, tangents (default; `face=old` keeps the old look). The glTF
   exporter dropped the vertex alpha when the material node tree used it ("alpha-only vertex colour" path); fixed by not
   wiring it in the node tree. `fp_arms.py`: no vertex colours on the arms.
6. Unity install #1 failed in `PistolModsInstall` (FindAnyObjectByType returned the rifle view model): fixed there and in
   `FPGripPass.OpenVm`. Install + verify pass.
7. First-person hands, iterations (captures in `unity/captures/`, orbit views):
   - player arms on the pistol + contact-solved fingers: the support hand floated (mirror plane from the wrong mesh: the
     inactive FP hands v2 had been picked as "largest mesh"; then a wrong lateral axis);
   - found the real problem: the hold clip puts the palm behind the grip, fingers over the slide. Remounting the pistol in
     the hand swung the whole arm across the view → made the pistol **weapon-driven** (`ViewModelArmsRig`, IK on both
     arms, elbow poles, shoulders centred), ADS pushed to 0.46 m;
   - a wrong `down` axis (grip mods inactive in the editor, sign test circular) put the wrist above the bore; fixed by
     taking down from the muzzle's offset above the bounds centre.
   - The rifle weapon-driven trial put the hand on the receiver → rifle left clip-driven (flag), support grip by contact.
8. Eyes re-tinted (`tex/eye_brown.png`); outer shell layers fade at the mask edge. Final chain run, verify pass,
   Edit Mode 268/268, final captures (face / fp / tp sets, ≤6 cameras each).

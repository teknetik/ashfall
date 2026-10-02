# Outer Berms hero landmarks (2 Oct 2026)

Carl asked for the Outer Berms to grow to about 500 m across with enemy sites spread out. The Berms expanse pass
(`art/berms_expanse_20261002`) builds the terrain, encounters and site dressing. This pass makes three original
landmarks that read from 200–400 m and anchor sites. It covers assets only: prefabs, materials and evidence. Scene
placement belongs to the expanse pass, and this pass never opened the scene.

| Prefab | What it is (lore) |
| --- | --- |
| `Prefabs/BermsExpanse/Landmarks/CaravanHaulerWreck.prefab` | A Karaveen caravan's multi-axle cargo hauler. Feral droids ambushed and stripped it long ago. It has a crushed cab, a jury-rigged solar frame, a torn and patched canvas over bare hoops, missing wheels and spilled crates. It sits level on its axles, so it gives cover. |
| `Prefabs/BermsExpanse/Landmarks/AquiferDerrick.prefab` | A Great-Rebuild aquifer wellhead under a riveted steel lattice pump derrick. Around it are flanged valves and hand-wheels, pipes into the ground (one broken), a collapsed control hut and a broken solar frame. It shows the water infrastructure that keeps Ward alive. |
| `Prefabs/BermsExpanse/Landmarks/TubePylonFall.prefab` | A goods-only Quantum Tube support pylon: cracked concrete, exposed rebar and an alloy cradle with dead teal inlay. It leans 4° toward a fallen tube section half-buried in sand at its foot. The tube has no windows or doors, so nothing suggests passenger transport. |

## Pipeline

All steps are headless and memory-capped. Blender runs through `~/.local/state/ward-programme/blender.sh`; Unity runs
once through `unity.sh`, with `-nographics`.

1. **Concepts.** The Codex CLI image tool (ChatGPT plan, free) made them with `concepts/run_codex.sh`. Prompts and
   reference chains are in `concepts/prompts.json`; the `.txt` and `.png` files stay local.
   - Each landmark started with one hero three-quarter view. Further views were generated with that view as the
     reference (`-i`).
   - `derrick_hero` came back on a dark vignette. `derrick_front` is an edit of it onto neutral grey.
   - `pylon_hero` drew the tube about 4 m across beside a short pylon. The pylon and tube were therefore split into
     separate concepts and models, each fitted to its true size.
2. **Meshy.** `gen_model.py` sends a multi-image-to-3D request with:
   - the first image as the main view, then side and back;
   - `ai_model: latest`, `geometry_resolution: 2k`, triangle remesh to 50–90k, `save_pre_remeshed_model`;
   - PBR at 4k (base and normal 4k, metal/rough 2k), `remove_lighting`, and a texture prompt per subject.

   The key comes from `.env` into the environment only. Requests and task IDs are in `record.json`.
3. **Inspection.** `review.py source|channels` renders:
   - four axis views and two three-quarter views;
   - player-height views at 6 m and 2.5 m beside a 1.8 m figure;
   - a back-face check and a 300 m read through an 8× lens;
   - flat renders of the metallic, roughness and base-colour channels, to see where metal lands on the model.

   `debug_vis.py` colours the faces by two-sided class. `sheet.py` makes contact sheets. Renders stay under
   `*/a1/review/` and `renders/`, untracked.
4. **Prepare.** `prepare.py` writes `Art/BermsExpanse/Landmarks/<Id>/` and `berms-landmarks.json`. For each landmark it:
   - aligns the footprint's minimum-area rectangle to the axes, with the front at Unity +Z;
   - scales uniformly: hauler to 10.5 m long, derrick to 13.0 m tall, pylon to 14.0 m tall, tube to 2.75 m tall
     (the tube comes out 13.4 m long);
   - tilts the pylon 4° about its base centre and lowers it until its raised edge meets the ground. The low edge is
     buried to −0.60 m;
   - places the tube with its sheared, cable-spilling end toward the pylon's foot, running out along the old line;
   - recentres the landmark so the footprint centre is at the origin and the ground at y = 0;
   - keeps LOD0 as Meshy's topology, UVs and normals;
   - builds LOD1 and LOD2 as welded copies, collapse-decimated to 35 % and 10 % and smooth-shaded at 35°;
   - runs the two-sided repair (next section) on every LOD;
   - writes the embedded maps out byte for byte;
   - fits the box colliders (below).

   The GLBs come from Blender's exporter without images.
5. **Masks.** `textures.py` (`uv run --with pillow --with numpy`) builds the URP Lit mask: R = glTF metallic,
   G = 1, A = 1 − roughness, kept at the delivered 2k.
6. **Unity.** `Editor/BermsLandmarksImport.cs` runs
   `unity.sh <log> AthenHill.Editor.BermsLandmarksImport.RunBatch -nographics -quit --steps import,prefab,verify`.
   - Texture importers: BC7, mip streaming, aniso 8, clamp, max 4096 for base and normal and 2048 for the mask.
   - glTFast imports the GLBs.
   - Each part gets an editable URP Lit material in `Art/BermsExpanse/Landmarks/Materials/`, with smoothness
     ×0.85.
   - Each prefab has a LODGroup at 0.30 / 0.09 / cull 0.012 with no fade.
   - LOD0 and LOD1 cast shadows; LOD2 does not, since it starts beyond the 150 m shadow distance.
   - Colliders are BoxColliders under `Colliders/`. Static flags are Occluder, Occludee and ReflectionProbe.

   The run on 2 Oct at 10:40 reported `problems: none`. Evidence is in `unity/evidence/berms-expanse/20261002/landmarks/`:
   `import.json`, `verify.json` and `unity-import.log`.

### Two-sided repair

Meshy's thin sheets have mixed winding: torn canvas, sand drape, cloth flaps and the derrick's crown deck. URP Lit
culls back faces and does not flip normals under Cull Off, so these sheets would show holes. The repair works like
this:

- For each face, up to 64 rays per side are cast from just in front of it and just behind it. The rays cover the two
  hemispheres, never below the horizon, against the model's BVH.
- If a viewer outside the object could see only the back of a face, the face is flipped.
- If the face is visible from both sides, a flipped copy is added.
- Corner normals are carried over and negated on flipped corners.

| LOD0 | Flipped | Duplicated (two-sided) |
| --- | --- | --- |
| Hauler | 907 | 399 |
| Derrick | 217 | 216 |
| Pylon | 50 | 37 |
| Tube | 51 | 74 |

### Colliders (`prepare.py fit_colliders`)

- Surface samples in a height band above the ground are rasterised on a grid. Enclosed holes are filled, with
  optional closing across 1-cell gaps.
- The result is split into connected masses. Each mass gets an oriented minimum-area box.
- A box is cut in two while it is under the fill threshold or longer than the split length. The cut is a guillotine
  cut along either box axis, choosing the pair with the best fill.
- Box height follows the continuous stack of geometry inside the footprint. Boxes start at −0.5 m so they still meet
  uneven terrain.
- Slivers are dropped (side under 0.15 m or area under 0.1 m²).

| Landmark | Boxes | Coverage |
| --- | --- | --- |
| Hauler | 3 | Up to 4.0–4.4 m |
| Derrick | 20 | Footings, legs, wellhead, pipe runs, hut, solar frame. Capped at 2.8 m, so shots pass through the open lattice. |
| Pylon | 7 | 4 on the footing, then the column stacked 1.4–7.0 m and 7.0–13.75 m |
| Tube | 5 | About 2.7 m tall |

The gap between the tube mouth and the footing stays open. `renders/<Id>/colliders_*.jpg` shows the boxes over the
model.

## Provenance

Every task cost 35 credits: latest model, 2k geometry (+5), 4k PBR texture. Each was accepted on its first attempt,
so no regenerations were needed.

| Task | Meshy task ID | Source images | Credits |
| --- | --- | --- | --- |
| hauler_a1 | 01a0fbdc-d6ca-75c4-9217-f96393fac001 | hauler_hero, hauler_side, hauler_back | 35 |
| derrick_a1 | 01a0fbdc-e644-7115-8134-3d790808f412 | derrick_front, derrick_side, derrick_back | 35 |
| pylon_a1 | 01a0fbdc-f5d9-77ed-8157-3715cf46a44e | pylon_front, pylon_side, pylon_back | 35 |
| tube_a1 | 01a0fbdd-0577-74c7-9240-e0249999967f | tube_front, tube_side, tube_back | 35 |

The total is **140 credits**, pre-approved as routine generation under AGENTS.md §5. The balance went from 442 to
272; the ranged-enemies agent was generating at the same time. Downloads (`model.glb`, `pre_remeshed.glb`, 4k
textures, thumbnails) stay local per `.gitignore`. The full-detail pre-remesh source is kept beside each model.

## Result in Unity

| Prefab | Size X × Y × Z (m) | Triangles LOD0 / LOD1 / LOD2 | Colliders | Best silhouette |
| --- | --- | --- | --- | --- |
| CaravanHaulerWreck | 10.50 × 4.39 × 5.63 | 80,027 / 28,134 / 19,815 | 3 | +Z broadside (lockers, water drums, torn canopy); cab at −X, crates at the +X tail |
| AquiferDerrick | 11.32 × 13.00 × 7.37 | 89,313 / 31,380 / 13,300 | 20 | +Z: ladder leg left, wellhead centre, hut and solar frame on the right (−X) |
| TubePylonFall | 13.38 × 14.34 × 21.06 | 101,482 / 35,535 / 11,300 (pylon + tube) | 12 | ±X broadside: leaning pylon at +X/+Z, tube running out to −X/−Z |

- **Texture memory:** 192 MB with every mip resident, before streaming. Each of the four parts has a 4k BC7 base, a
  4k normal and a 2k mask.
- **Index format:** LOD0 meshes are UInt32 (more than 65k vertices).
- **LOD switches** (LOD bias 2, 60° field of view): the hauler goes to LOD1 at about 60 m and LOD2 at about 200 m.
  The pylon group, sized at 21 m, switches at about 120 m and 400 m. All three cull beyond 1.5 km, so none culls inside
  the Berms.

`handoff.json` gives each prefab's path, size, footprint, bounds, collider boxes, best side and placement notes.

## Inspection findings

These checks used Blender Cycles renders: views, player height, 300 m read, back faces, channels and LODs.

- **Hauler.** Strong silhouette, and it reads as a truck at 300 m. The crushed cab, patched canvas over bare hoops,
  missing wheels with bare hubs, spilled crates and solar frame all came through. Metal is only on worn edges. Canvas,
  sand and paint are dielectric. Its canvas and sand drape had the most mixed-winding faces, all repaired.
- **Derrick.** The lattice came out as real open members, with cross-bracing, a caged ladder and the crown sheave.
  The wellhead, valves, gauges (blank dials) and pipes, including one broken open, are all readable. The rusted
  lattice is dielectric.
- **Pylon.** Clean concrete forms: stepped footing, rebar breach, scorch craters, rubble and sand apron. The alloy
  cradle is the only metal.
- **Tube.** Ribbed casing with dark teal bands and a sheared, cable-spilling mouth. The casing is metallic and the
  sand is not.
- **All models.** No baked text and no strong baked lighting. Each is one loose mesh body, with no floaters beyond
  small debris.

## Known defects and open items

- **Hauler LOD2 is 19.8k triangles (25 %), not 10 %.** Meshy's many small UV charts stop Blender's collapse
  decimation; repeated passes gained nothing. The derrick's LOD2 reached 15 %. Both are acceptable at 200 m and
  beyond, and LOD2 casts no shadows.
- **The hauler's grime and rust are fairly even across the body,** rather than gathered at joints and drains as
  AGENTS.md §4 asks. The derrick's hut doors read as weathered planks more than steel. The tube casing is rather
  clean and uniform.
- **The pylon's lean was added in Blender;** the concept was upright. Its low footing edge is buried to −0.60 m, and
  its sand and rubble apron is about 7.4 m wide.
- **The tube came out 2.75 m in diameter and 13.4 m long.** Its buried end is a sand ramp rather than a broken face.
- **Hauler colliders** run to about 4.4 m over the whole hull, including above the lower cab. The rear box also
  reaches about 0.8 m out over the crates, which leaves an invisible wall above the crates.
- **Interior faces seen only through small openings may have been missed.** The two-sided test samples 64 rays per
  side, so some faces behind the cab window or canvas tears could keep their winding. Check this in a first-person
  view in the game.
- **LOD changes pop** because fade mode is none.
- **Not yet seen in Unity lighting or the native player.** The native lookbook and frame-time A/B belong to the
  batch's combined test. Not yet accepted by Carl.

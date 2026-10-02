# Salvage shop interior hero props (1 Oct 2026)

Carl asked for the Salvage shop to become walkable, "open to trade and have the equipment in there", where the player
upgrades the scrap pistol (the fabrication station moves from the field tool cart into the shop). These are the shop's
equipment props. Assets only: the shop architecture, scene placement and gameplay wiring belong to the Salvage shop pass
(`Editor/SalvageShopPass.cs`).

## Pipeline

1. `generate.py`: Meshy text-to-3D, meshy-7.1 preview (remesh, triangles) then refine with PBR. Key from `.env`
   `MESHY_API_KEY`, loaded into the environment only and never written to disk. Resumable: task IDs and requests are
   in each `<attempt>/record.json`. `--retry <name>` moves a rejected attempt to `<name>/attemptN/` (at most two).
2. `review.py` (Blender 5.2 headless through `~/.local/state/ward-programme/blender.sh`, Cycles CPU at 48 samples,
   denoised):
   - `source <attempt>` writes stats (triangles, loose parts, maps) and textured front, side, back and three-quarter
     views, three views at 0.8 m and an orthographic front with a 0.1 m grid, all next to a 1.8 m figure.
   - `lods <SS_id>` compares LOD0 and LOD1 with the extracted maps, the screen overlay, the light point (cyan dot) and
     the use point (yellow disc). For the bench it also renders the view from the use point.
3. `prepare.py` (Blender) does the following:
   - joins the parts and removes the parts the spec names;
   - turns the front to Blender −Y, which is Unity +Z;
   - applies one uniform scale and puts the base on the floor at the footprint centre;
   - keeps LOD0 as the delivered topology and normals;
   - builds LOD1 by welding the seams, collapse-decimating to 30 %, clearing custom normals and smoothing by 40°;
   - copies the maps out byte for byte;
   - measures the colliders, screen panel, print head, use point and light point.

   The output goes to `unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props/<SS_id>/` and
   `Props/salvage-shop-props.json` (Unity axes). The GLBs come from Blender's own glTF exporter, without images.
4. `textures.py` (`uv run --with pillow --with numpy`) makes:
   - the URP Lit masks (R = glTF metallic, G = 1, A = 1 − roughness);
   - the 512 px metallic/roughness previews in `<attempt>/maps/`;
   - the authored fabricator display `Materials/SS_FabScreen_Display.png` (original art with no text or logos, drawn at
     the screen quad's aspect and stored at 2048 × 512).
5. `Editor/SalvageShopProps.cs`
   (`unity.sh <log> AthenHill.Editor.SalvageShopProps.RunBatch -nographics --steps build,verify`) does the following:
   - sets the texture importers (BC7 compression, streamed mips, anisotropic 8, clamp);
   - builds the URP Lit materials;
   - builds the prefabs `Prefabs/SalvageShop/SS_*.prefab` with LODGroup 0.30 / cull 0.02, box colliders, shadows on,
     light-probe GI and the OccludeeStatic flag;
   - for the bench, adds the `Screen` quad (`SS_FabScreen.mat`, RealtimeEmissive), `Use point` and `Light point`;
   - writes `unity/evidence/salvage-shop/20261001/props-verify.json`.

   It never opens a scene.

## Provenance

| Attempt | Preview task | Refine task | Credits | Result |
| --- | --- | --- | --- | --- |
| workbench | 01a0f912-e1b7-75ca-92d3-46434b58a689 | 01a0f914-94fd-73eb-b0d5-b859df643b8e | 30 | Rejected. It reads as a machinist's bench: no rear frame or gantry, the screen sits on a post and carries baked UI marks. |
| workbench_b | 01a0f915-df70-7546-89cd-fce287d2030d | 01a0f917-cf1a-767e-a808-6641a8b99c5a | 30 | Accepted mesh (regeneration 1). Its 2k texture was soft and smeared on the worktop at 0.8 m. |
| workbench_b4k | (same preview) | 01a0f924-5831-71f9-9456-dccae15c867b | 10 | **SS_Workbench.** The same mesh re-textured at 4k: crisp graphite steel, a muted safety-yellow print head, a timber-edged worktop. |
| parts_rack | 01a0f912-e988-7652-af86-47d31019b79f | 01a0f915-1586-76d0-9983-c488394051b0 | 30 | **SS_PartsRack**. |
| parts_rack_heavy/attempt1 | 01a0f91d-368b-74b3-ab80-8c0a3ec50140 | 01a0f91f-6361-7625-9624-f69a739dda56 | 30 | Rejected. An empty saturated-orange stand with one motor underneath; no torso shell and no drum. |
| parts_rack_heavy | 01a0f928-ebdc-70d9-9520-1f04f6a3c8b4 | 01a0f92a-9b4d-707f-929e-2b643db28edb | 30 | **SS_PartsRackHeavy** (regeneration 1). |

Total **160 credits** (pre-approved routine generation, AGENTS.md §5). Downloads, renders and maps stay local per
`.gitignore`.

## In Unity

| Prefab | Size W × H × D (m) | LOD0 / LOD1 triangles | Maps (BC7, streamed) | Notes |
| --- | --- | --- | --- | --- |
| SS_Workbench | 2.20 × 2.13 × 1.17 | 84,595 / 25,355 (incl. the 2-tri screen) | 4k base, 4k normal, 2k mask = 48.0 MB | Worktop top 0.864 m, 2.2 × 1.15 m. Drawers on the user's right; the vice is stored on the lower shelf (Meshy did not bolt it to the top). |
| SS_PartsRack | 1.23 × 2.20 × 0.57 | 114,135 / 34,213 | 2k × 3 = 16.0 MB | Meshy made a standard 1 : 1.8 bay, so it is fitted by height (a 2.0 m width would make it 3.6 m tall). Two side by side make a 2.5 m run. |
| SS_PartsRackHeavy | 1.29 × 1.40 × 0.68 | 80,979 / 24,273 | 2k × 3 = 16.0 MB | Fitted by height. A machine/power unit on top; a winch motor, cable reel and drum below. |

The fabricator display is 2048 × 512, BC7, not streamed, 1.3 MB. All textures together come to 81.3 MB with every mip
level resident.

Positions in the bench's local space (front = +Z, pivot at the floor centre):

- `Use point` (0, 0, 1.083): 0.8 m in front of the worktop centre would put the player's 0.35 m capsule against the
  bench, so this point sits 0.50 m clear of the worktop's front edge (z 0.583).
- `Light point` (0, 1.588, 0.224): at the print head's lens, 6 cm in front of its body and 12 cm above its tip, clear of
  the geometry.
- `Screen`: centre (0.009, 1.055, −0.103), facing +Z; quad 0.822 × 0.224 m, set inside the plate's bezel and 8 mm in
  front of the creased plate.

Colliders:

- `COL bench body`: 2.2 × 0.864 × 1.17 m.
- `COL rear frame`: 2.18 × 1.27 × 0.09 m, worktop to frame top. The print head overhang is left open.

## Inspection notes and remaining issues

- Renders are in `<attempt>/review/`: source views, closes at 0.8 m and LOD comparisons. The bench's
  `lod0_use_view.png` is the player's view from the use point.
- Meshy small parts on the stocked rack (bolt piles, small motors) are lumpy at 0.8 m. They read as salvage stock but
  not as machined detail. One grey bin stack on the rack runs through the second shelf lip.
- The heavy rack's machine has a tiny stamped mark on one side; it is not readable as text. The yellow paint chipping
  on its beams is fairly even rather than gathered at contact points.
- The bench's metallic map is almost all dielectric (painted steel). The parts rack's metal is on the dark motor parts
  only; the orange and blue regions are non-metal.
- LOD1 softens the print head and shows UV-seam smearing at 0.8 m. It is meant for 13 m and beyond. A 0.3
  screen-height switch keeps it out of normal interior range.
- Not yet judged in the game's lighting. These are Blender and batch checks only; the native lookbook belongs to the
  shop pass's batch. Not yet accepted by Carl.

    # Athen Hill — Codex Build Guide
## An Old-Athen-type 2001 sci-fi MMO city MVP

Drop this file in an empty repo as `AGENTS.md` (or keep it next to `AGENTS.md` and paste the **Master Prompt** at the bottom into Codex on **high / Astra** reasoning).

This is a **fan homage MVP**, not a Funcom product. Do **not** rip Anarchy Online meshes, textures, UI chrome, music, names of official NPCs, or logos. Rebuild the *feeling* of 2001 Clan Old Athen from original geometry, original names, and original copy.

---

## 0. How the good-looking Astra games are actually being made

The viral Codex + Blender MCP games (Anshu’s 45-minute dystopian prototype, Void Explorer, Little Ritual, Sunwake) share one loop. They are **not** one-shot “write a game” prompts.

```
1. Connect local Codex to a live Blender MCP session.
2. Write a tight concept: fantasy + mechanics + art direction + hard constraints.
3. Generate TARGET CONCEPT ART first (Codex image gen). Freeze 4–8 hero frames.
4. Greybox the playable loop in TypeScript + Three.js until WASD + camera + collide work.
5. Model hero assets in Blender against those frames. Export glTF. No Sketchfab / no AO dumps.
6. Generate PBR textures from the same concept art. Bake / atlas.
7. Drop assets into the running game.
8. Capture FIXED-CAMERA screenshots of the live game.
9. Diff screenshot vs concept art (palette, silhouette, light direction, density, roughness).
10. Change ONE family of things per iteration. Re-render. Repeat until 60 fps AND close to the frames.
```

What actually makes it look expensive:

- **Image gen is the art director.** Astra is strong at matching a picture it can see. Without frozen target frames it drifts into generic shiny Three.js slop.
- **Blender is for authored silhouettes**, not for the whole city as one mega-mesh. Buildings, the hill tree, whompah, grid kiosk, PC, NPCs — those get real meshes. Pavement, sky, distant walls can be instanced / procedural.
- **The judge is a screenshot, not a vibe.** Same camera, same time of day, every pass.
- **60 fps is a hard gate**, not a later optimization. Triangle budget and draw-call budget are set before detailing.
- **High reasoning + overnight /goal loops.** People let Astra run, then a critic agent refuses to accept “done.”
- **No external marketplace assets.** The impressive demos model in Blender and texture from image gen so the style stays coherent.

Official-adjacent stack that keeps winning for browser MVPs:

- TypeScript + Vite
- Three.js (WebGL2 first; WebGPU only if you already have a working frame)
- Rapier or simple AABB/capsule collision
- glTF / GLB from Blender
- Web Audio for one ambient bed + a few one-shots
- Playwright or a `window.__GAME__` debug hook so the agent can screenshot and inspect state

Do **not** start in Unity/Unreal for this MVP. The winning loop is: Codex writes the runtime, Blender MCP authors the look, browser is the preview.

---

## 1. Machine setup (human, once)

### Required

- Blender 4.2+ (5.x LTS is what current Astra writeups use)
- Node 20+
- Codex CLI or Codex desktop, signed in, **local** session (Astra is not for Codex cloud)
- `uv` from https://astral.sh — **not** `pip install uv`

### Blender MCP (ahujasid/blender-mcp)

```bash
# install uv, then:
uvx blender-mcp install-addon
```

In Blender:

1. Edit → Preferences → Add-ons → enable **Interface: MCP for Blender**
2. 3D Viewport → `N` → **MCP for Blender** → **Start MCP Server**
3. Leave Poly Haven / Sketchfab / Rodin **off** for this project (style contamination)

Codex:

```bash
codex mcp add blender -- uvx blender-mcp
```

If the GUI client cannot find `uvx`, put the **absolute path** in `~/.codex/config.toml`:

```toml
[mcp_servers.blender]
command = "/absolute/path/to/uvx"
args = ["blender-mcp"]
```

Sanity check inside Codex:

> Use Blender MCP. Inspect the scene. Create a 2m blue cube named `PROBE_CUBE` at origin, add a sun and camera, render a 512px preview, save `previews/probe.png`. If that fails, stop and report the error. Do not invent a fallback that skips Blender.

### Project folders

```
athen-hill/
  AGENTS.md
  ATHEN_HILL_CODEX_GUIDE.md
  refs/                 frozen concept frames (do not overwrite)
  blender/
    scenes/             versioned .blend
    exports/            glb
    previews/           blender stills
  public/
    assets/             runtime glb + textures + audio
  src/                  TypeScript game
  tools/
    shots/              fixed-camera game screenshots
  package.json
```

---

## 2. Product definition — what “MVP clone” means

### Fantasy (one paragraph)

You are a new Clan colonist dumped into a compact, war-scarred desert-edge city on a notum-rich world. Marble walls, arched gates, a shopping avenue, and a raised plaza dominated by one impossible ancient tree. Vendors hawk junk under holographic boards. A Grid kiosk hums in the north-east. A whompah gate sits south. The air is dusty gold, the architecture is 2001 sci-fi: chunky bevels, stone plinths under dark metal towers, emissive cyan slits, slightly muddy textures, long shadows. You can walk, talk to a handful of NPCs, open a shop, and use the Grid kiosk as a “leave the demo” beat.

### Playable loop (must ship)

1. Load into a third-person character on the west gate plaza.
2. Walk the avenue to **Hill Tree**.
3. Talk to 4 NPCs (one vendor, one fixer, one guard, one loafer).
4. Open the **Basic General** stall UI and buy/sell one trash item.
5. Use the **Grid kiosk** (short tunnel VFX, then a “sector map” overlay — no second zone required).
6. Optional: stand in the whompah ring and get a “destination offline” bark.

### Explicitly out of scope

- Multiplayer, chat servers, accounts
- Full nano/IP/skill system
- Dynamic missions / instanced dungeons
- Vehicles, yalm, apartments
- Combat beyond a later stretch goal
- A second playfield (West Athen, Wartorn)
- Exact Funcom UI windows

### Performance contract

- 1920×1080, medium laptop GPU
- **60 fps** while walking the avenue with all NPCs on screen
- ≤ 250k triangles on screen
- ≤ 80 draw calls (atlas + instancing)
- One HDRI + one sun + one fill + baked-ish emissives
- No realtime GI

---

## 3. Art direction — 2001 Old Athen, rebuilt

Reference the *layout and mood* of Clan Old Athen c.2001–2004, not the current engine.

### Mood board words

dusty gold hour, two suns optional but one strong key light is enough, pale stone pavement with large tiles, dark gunmetal buildings on stone plinths, bevelled sci-fi art-deco, cyan/teal holographic panels, red Clan banners faded, one enormous gnarled tree on a grassy rise, marble wall with arched gates west, wreckage glow to the east, slightly soft textures, no PBR chrome overkill, no cyberpunk rain, no Unreal 5 lumen.

### Palette

| Role        | Hex     | Use                          |
|-------------|---------|------------------------------|
| Sand stone  | `#C4A574` | pavement, wall trim        |
| Dust haze   | `#B8956A` | fog, ambient               |
| Gunmetal    | `#3A4149` | building bodies            |
| Plinth      | `#8B7A63` | building bases             |
| Banner red  | `#8B2E2E` | Clan cloth                 |
| Holosign    | `#3EC7C2` | terminals, Grid, shop UI   |
| Notum glow  | `#7D5CFF` | rare accents only          |
| Foliage     | `#4A5A32` | hill grass, tree           |
| Sky         | `#6F8AA8` → `#E2C9A0` | late afternoon        |

### Camera / scale

- 1.0 unit = 1.0 meter
- PC height 1.8 m, capsule r=0.35
- Buildings 6–14 m
- Hill Tree 18–28 m to crown
- Playable disk ≈ 120 m × 90 m (tiny, readable, dense)
- Third person: boom 4.2 m, look-at +1.5 m, collision on boom

---

## 4. Layout — compressed Old Athen

Build a **readable miniature**, not a 1:1 map. Keep the landmarks people actually used as meeting spots.

Origin = center of Hill Tree trunk.

```
                 N
                 │  GRID KIOSK (y=+38)
                 │  VANGUARD HALL (y=+32, x=+8)
     WEST GATE   │
   (x=-48) ══════╪════════ EAST WRECK VISTA (x=+52)
                 │
   SHOP ROW W    HILL TREE / OA HILL      SHOP ROW E
   (x=-18)       (0,0)                    (x=+16)
                 │
                 │  BASIC GENERAL (x=-8, y=-10)
                 │
                 │  WHOMPAH (y=-36)
                 S
```

Landmarks that must exist and be nameable:

| ID            | What it is                                      | Why |
|---------------|--------------------------------------------------|-----|
| `hill_tree`   | Titanic ancient tree on a raised grassy knoll    | The meeting spot |
| `oa_hill`     | Plaza + GMS-style market terminals around tree   | Social center |
| `shop_row_e`  | 4 shop fronts in a line, stone + metal           | The shopping mile |
| `shop_row_w`  | 3 shop fronts + Finest Edition luxury facade     | Depth |
| `west_gate`   | Marble wall, two arched gates, Clan banners      | Spawn / West Athen exit |
| `vanguard_hall` | Blocky HQ with a tall antenna / crest mass     | North landmark |
| `grid_kiosk`  | Small raised pad + humming terminal + ring light | Fast-travel beat |
| `whompah`     | Two stone rings facing each other, energy pane   | South landmark |
| `mission_slab`| Three waist-high terminals on a plinth           | NPC hook |
| `billboard`   | Big holographic board on the hill                | Skyline read |
| `east_wreck`  | Broken wall + rust beams framing a canyon glow   | Wartorn hint |

Collision: walkable pavement, stairs up the hill (not a ramp-only blob), shop porches, gate tunnels you can stand in. Interiors of shops can be 2-meter deep stage sets with a dark back wall — do not model full interiors.

---

## 5. Characters

### PC (`player_colonist`)

One body. No character creator.

- Lean human, mid 20s, androgynous-readable or pick one sex and commit
- Starting “Omni-reject / Clan recruit” kit: scuffed jacket, cargo pants, one shoulder pad, cheap wrist terminal
- Animations: idle, walk, run, talk-gesture. No combat set for MVP
- Target: 12k–18k tris, one 2k atlas
- Rig: simple humanoid, glTF clips

### NPCs (four + ambient)

| ID | Role | Placement | Bark |
|----|------|-----------|------|
| `npc_mira` | Basic General vendor | shop porch west of hill | sells a Medkit and a Water Flask |
| `npc_torr` | Fixer / mission hook | mission_slab | “Wartorn’s quiet today. Don’t get used to it.” |
| `npc_vex` | Gate guard | west_gate | faction flavor, blocks nothing |
| `npc_linn` | Loafer | under hill_tree | tells you to meet people “on the hill” |
| `npc_drones` | 3 ambient walkers | loop waypoints | no dialogue |

NPC kitbash from the same body as the PC with different jackets / hats / banners. Do **not** spend the first day on unique sculpts.

Interaction: approach, `E`, subtitle + 2-choice dialogue, one of them opens shop UI.

---

## 6. Runtime architecture Codex should propose and then build

Keep it boring and inspectable.

```
src/
  main.ts                 boot, resize, loop
  game.ts                 states: boot | play | shop | grid
  input.ts                pointer lock optional; always-on RMB rotate + WASD
  player.ts               capsule move, gravity, slope
  camera.ts               third person boom
  world.ts                gltf load, collision meshes, lights, fog
  npc.ts                  billboard nametags, idle/walk, interact
  ui.ts                   2001-adjacent HUD: health pip, nano pip, hotbar 6, chat log fake
  shop.ts                 simple buy/sell
  debug.ts                window.__ATHEN__
```

`window.__ATHEN__` **must** expose:

```ts
{
  version: string
  state: string
  player: { x, y, z, yaw }
  fps: number
  draws: number
  tris: number
  shot(name: string): Promise<string>  // saves tools/shots/<name>.png from a named camera
  goto(landmark: string): void
  timeOfDay: number
}
```

Named cameras (create these as objects in the scene, never eyeball):

- `cam_gate`
- `cam_avenue`
- `cam_hill`
- `cam_grid`
- `cam_whompah`
- `cam_hero` (over-shoulder of PC on the hill)

---

## 7. Asset production rules for Blender MCP

### Modeling rules

- Metric units. Apply scale. Origin at ground center.
- Bevel important edges (0.02–0.06 m). 2001 AO read as *chunky bevels*, not subdivision clay.
- No overlapping sloppy boolean garbage. If a boolean is used, apply and clean.
- Lightmap / UV0 unique for hero props. UV1 for tiling.
- Name everything: `BLD_shop_e_01`, `PROP_terminal_gms`, `CHR_player`, `COL_hill`
- Separate `COL_*` meshes (simple boxes/convex) from render meshes.
- Export glTF Binary, Y-up, +Z forward as Three.js expects; test one cube first.
- One material per object family after atlas. Do not ship 40 Principled shaders.

### Build order in Blender (do not skip)

1. Blockout: cubes and planes matching the layout map. Save `blender/scenes/01_blockout.blend`.
2. Hero: Hill Tree. This is the silhouette of the whole demo.
3. West gate + marble wall module (array the wall).
4. One shop module, then instance / vary 7 fronts.
5. Vanguard hall massing.
6. Grid kiosk + whompah rings.
7. Terminals, banners, crates, benches, holo-boards.
8. PC, then NPC variants.
9. Lighting scene with the game’s sun angle. Render the six named cameras.
10. Export `public/assets/world.glb`, `player.glb`, `npcs.glb`.

### Texture rules

- Generate concept close-ups first (stone tile, metal panel, banner, bark, holographic glass).
- 2k for hero tree + PC. 1k for shops. 512 for crates.
- Slight film grain / baked dirt. Avoid pristine Substance showroom.
- Emissive only on holosigns, Grid ring, shop window slits.

### After every Blender session

Render the six cameras to `blender/previews/` and stop if the tree does not read at 256px thumbnail.

---

## 8. Visual iteration scorecard

Copy Anshu / Void Explorer: never say “looks better.” Score the same frame.

For each of `cam_hill`, `cam_avenue`, `cam_gate`:

| Trait            | 0–5 | Notes |
|------------------|-----|-------|
| Palette match    |     | vs frozen concept |
| Sky / haze       |     | dusty gold, not steel HDRI |
| Silhouette       |     | tree + gate + hall readable |
| Light direction  |     | same key as concept |
| Material roughness |   | dusty, not chrome |
| Density          |     | props, banners, terminals |
| Scale            |     | doors ~2.2 m, tiles large |
| HUD integration  |     | chrome sits in world |
| fps @ 1080p      |     | must stay ≥ 58 |

Acceptance: all three hero cams ≥ 4 on palette/silhouette/light, and fps gate held.

Change **one family** per iteration: lighting OR materials OR geometry OR props OR HUD. Not all five.

---

## 9. Phased work plan for Codex

Run these as separate sessions. Commit after each phase. Do not start phase N+1 if phase N acceptance fails.

### Phase 0 — Repo and probe (30–60 min)

- Vite + TS + Three.js
- Empty canvas, stats, `window.__ATHEN__`
- Blender probe cube round-trip into the scene as glb
- Confirm MCP render works

### Phase 1 — Greybox city (2–4 h)

- Layout from section 4 in raw primitives **inside the game**
- Player capsule, gravity, third-person camera
- Landmark teleports for the agent
- Fog + sun + hemi
- No textures yet

Acceptance: walk west gate → tree → whompah → grid without falling through.

### Phase 2 — Concept art freeze (1–2 h)

Use Codex image gen. Produce and **save, never overwrite**:

- `refs/01_hill_wide.png` — tree plaza, late afternoon
- `refs/02_avenue.png` — shop row looking north-east
- `refs/03_west_gate.png` — marble arches from inside
- `refs/04_grid.png` — kiosk close
- `refs/05_whompah.png`
- `refs/06_pc_threequarter.png`
- `refs/07_vendor.png`
- `refs/08_ui_overlay.png` — HUD mock only

Prompt seed for image gen:

> Still from a 2001 sci-fi MMORPG city, late afternoon on a dusty colony world. Raised plaza with one enormous ancient tree. Chunky bevelled buildings: stone plinths, dark metal towers, cyan holographic shop signs, faded red banners. Large pale stone tiles. Marble wall with arched gates in the distance. Slightly muddy textures, physical lighting, not modern path-traced, not anime, not cyberpunk night. 16:9.

If a frame is wrong, iterate the **image**, not the game.

### Phase 3 — Blender world (longest art pass)

Model and export world + props to match `refs/01–05`.
Instance shops. Atlas.
Import into the greybox, replace primitives one landmark at a time.

### Phase 4 — PC + NPCs

Model PC against `refs/06`. Kitbash NPCs.
Idle + walk cycles (even 8-frame is fine).
Nametags + `E` prompt.

### Phase 5 — UI and verbs

HUD inspired by early-2000s MMO chrome (original shapes):

- bottom-center 6-slot hotbar
- left thin vitality / nano bars
- small chat/log
- cursor interact bracket
- shop window: list + buy
- grid overlay: 3 named nodes that just toast “link established”

### Phase 6 — Beauty pass against scorecard

Screenshot named cams. Diff to refs. Lighting, then materials, then props.
Birds or two hovering service drones only if fps allows.
One ambient audio bed + footstep + terminal hum + whompah thrum.

### Phase 7 — Polish and ship page

- Loading screen with the hill frame
- Pause / click-to-capture pointer
- README with controls
- `npm run build` static deploy

Stretch (only after Phase 6 scores):

- One dummy “leets at the east wreck” wander + click-to-punch
- Day/night slider
- Sit emote on a bench

---

## 10. Prompts Codex should use (copy-paste)

### A. First message in a new repo

```
Read ATHEN_HILL_CODEX_GUIDE.md and follow it as the project spec.

You are building Athen Hill, a small playable homage to a 2001 sci-fi MMO starter city
(Old-Athen-type): one PC, four talking NPCs, three ambient walkers, a compact nicely
rendered city disk.

Constraints:
- TypeScript + Vite + Three.js. No Unity, no Unreal, no downloaded game assets.
- Local Blender MCP is connected. Use it for authored meshes. If MCP is down, stop and say so.
- No Funcom / Anarchy Online IP in filenames, textures, audio, or copied meshes.
- Target 60 fps at 1080p. Budget 250k tris / 80 draws.
- Create window.__ATHEN__ as specified.
- Do not ask questions. Start Phase 0. After Phase 0, run the probe render.

Art direction: dusty gold late afternoon, chunky bevelled 2001 sci-fi, stone plinths under
gunmetal towers, cyan holosigns, faded red banners, one titanic hill tree, marble west wall.
Lighting must feel physical, not plasticky.

When you think a phase is done, screenshot the named cameras and score them with the
scorecard. You are not done if the live game does not resemble the frozen refs.
```

### B. Concept art

```
Use image gen to create the eight frozen refs listed in Phase 2.
Match the palette table. Show scale with a standing human in at least two frames.
Save under refs/ and do not overwrite accepted frames. Show me each frame before
moving on.
```

### C. Blender hero tree

```
In the open Blender scene, build CHR-less environment asset HILL_TREE:
- Trunk 2.4 m diameter at base, roots gripping a 14 m grassy mound
- Crown irregular, 22 m high, desert-ancient, a few dead limbs
- Keep under 30k tris
- Bark material dusty brown-grey, moss in forks
- Place at world origin
Render cameras cam_hill and cam_avenue. Compare to refs/01_hill_wide.png.
Fix silhouette until a 256px thumbnail still reads as THAT tree.
Export public/assets/hill_tree.glb
```

### D. Overnight beauty goal

```
/goal Make Athen Hill look as close as possible to refs/01–05 at 60fps.

Rules:
- Do not relax the fps gate.
- Use Blender MCP for any new authored mesh.
- After every change, call window.__ATHEN__.shot on cam_hill, cam_avenue, cam_gate.
- Score palette, silhouette, light direction, roughness, density separately.
- Change one family per iteration.
- Independent critic: compare shots to refs and refuse "done" until hill + avenue
  are obviously the same place as the paintings.
- Do not add new systems (combat, multiplayer, extra zones).
```

### E. Debug a broken scene

```
Player falls through the shop porch. Use window.__ATHEN__ to goto shop_row_e.
Log player y and nearby COL_ meshes. Inspect the glb collider in Blender if needed.
Fix collision only. Do not retouch materials in this pass.
Then screenshot cam_avenue and confirm fps unchanged.
```

---

## 11. HUD / audio notes

HUD should feel like a 2001 MMO overlay drawn originally:

- Dark semi-transparent panels, thin cyan hairlines, slight bevel
- Not Windows XP, not 2026 glassmorphism
- Fake chat lines already in the log: “Linn: Meet me on the hill.”
- Cursor: simple bracket, not a sword

Audio (generate or synthesize, original only):

- dry wind + distant market murmur
- stone footsteps
- terminal click
- whompah bass thrum
- one 40-second music bed, sparse, slightly Middle-Eastern / desert sci-fi, no copied AO theme

---

## 12. Legal / taste

- Original title: **Athen Hill**
- Original faction: **Free Column** (not Clan / Omni-Tek)
- Original travel toys: **Ring Gate** (whompah-like) and **Lattice Jack** (grid-like)
- If you show this publicly, call it a 2001 sci-fi MMO *homage city slice*
- Never ship extracted Funcom `.pfb` / textures / `.ogg`

---

## 13. Definition of done

A stranger can:

1. Open the web build
2. Recognize a tiny desert sci-fi city with a giant tree plaza in under two seconds
3. Walk gate → hill → shops → lattice jack without clipping
4. Talk to Mira and buy a flask
5. Hear the city hum
6. Hold 60 fps on a laptop
7. Take `cam_hill` and put it next to `refs/01_hill_wide.png` without cringing

That is the MVP. Everything else is a sequel.

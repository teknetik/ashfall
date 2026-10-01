# North avenue rebuild — Salvage, Repairs, Thread + Hide, Basic General (30 September 2026)

Carl (30 Sep 2026): "we recently rebuild a lot of the buildings but we still need to rebuild. general, salvage, thread
and repairs. same stone work, same signage, same weathering."

No new concept images were made: the brief was to match the accepted-in-progress hall district
(`art/hall_district_20260930`: shared Ward masonry kit, Masonry Lit weathering, the family signs). Nothing here is
accepted by Carl yet. Evidence: `unity/evidence/north-avenue/20260930/README.md`.

## What was built

The three shops stand on the same standard parcels as the hall district (facade 18.1 m from the avenue axis, 7.6 × 6.9 m,
the kept 0.5 m porch and step colliders) and reuse its `Shop` class (`art/hall_district_20260930/author_ward_shops.py`,
now importable: `main()` only runs as a script). Basic General keeps its own footprint and colliders.

| Building | Parcel (world) | Construction and story |
| --- | --- | --- |
| Salvage | (−18.1, 18), yaw 90 | Two storeys. Loading-bay roller shutter, olive personnel door, first-floor loading door (braced steel leaves, yellow safety rails) under a cantilevered yellow hoist beam with trolley, chain block, load and hand chains and a hook, stayed to the parapet. An old shell breach beside it: whole blocks shot out in a stepped outline, rebuilt in small rough stones in a fat mortar bed, the worst part under a riveted plate, impact scars and soot. Corrugated lean-to shed with stovepipe on the roof. |
| Repairs | (18.1, 9), yaw −90 | One tall storey and a low attic. 3.4 m workshop bay under a braced steel canopy (knee braces on the piers), glazed ochre door under a flat arch, sign on the upper wall. Its south side faces the cross street and Basic General: barred windows, ochre side door with lamp, a forge flue up the wall with rain cap and soot plume. Salvaged shipping-container workshop on steel sleepers on the roof. (A gas-bottle cage was dropped: the retrofit bin cluster already dresses that wall.) |
| Thread + Hide | (18.1, 18), yaw −90 | Two storeys. Lit display window (clear glass, warm LED strip, cloth-lined alcove: shelves of cloth bolts, a dress form in an indigo coat, folded hides, a laced hide), glazed teal door, indigo awning. Stone balcony on stepped corbels with tie rods and a painted railing; two glazed balcony doors; madder, ochre, indigo and bone cloth drying over the rail; hides laced into steel frames. Drying lines with cloth on the roof. |
| Basic General | (8, 0, 15.1), yaw 0 | The open booth in Ward stone: rear wall on the old line (its inner face stays exactly where Mira's shelves and the back panel touch it, z 14.0), cheek walls on the kept side colliders, two new stone front piers with caps, a riveted red box lintel that carries the existing family sign where it hangs, a stone attic course and coping above, a corrugated roof (continuous sheet, seen from the counter) falling to a rear gutter and downpipe, a roll-up security shutter box and guides, a slab porch and step matching the kept colliders, an aquifer service box, conduit and lamp on the rear. Counter dressing, Stock panels, back panel, sign and Mira are untouched. |

Shared: runoff under every cornice, coping, sill and lamp; rust under steel; wall-foot soil; old impact clusters and soot
(kit `ScarSet`); sheltered sand; 3–5 warm wall lamps per building on the Ward lighting clock (practical + night-only).

Triangles (LOD0 / LOD1): Salvage 73,583 / 19,068 · Repairs 66,459 / 17,248 · Thread + Hide 79,508 / 19,644 ·
Basic General 34,914 / 5,676. Signs: SALVAGE 5,704, REPAIRS 5,364, THREAD + HIDE 4,232.

New materials (Unity, `Art/WardShops/Materials`): WS_PaintOlive, WS_PaintOchre, WS_PaintYellow, WS_ContainerRust,
WS_ClothIndigo/Ochre/Madder/Bone and WS_Hide (VH_Linen set, double-sided), WS_LedWarm (emissive, on the light clock).

## Scripts and run order

Blender 5.2 headless, run with a clean environment (`env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup
--python-exit-code 1 -P …`; the Hermes Python on PATH breaks Blender's bundled modules):

1. `author_north_shops.py [-- salvage repairs thread_hide]` → `Art/WardShops/Models/<Shop>_LOD0/1.glb`, `<shop>.json`,
   `north-shops-source.blend`.
2. `author_basic_general.py` → `Art/WardShops/Booth/BasicGeneral_LOD0/1.glb`, `basic_general.json`, `basic-general-source.blend`.
3. `../hall_district_20260930/author_ward_signs.py -- salvage repairs thread_hide` → `Art/WardShops/Signs/Sign_<key>.glb`
   (only the named signs are rebuilt; `signs.json` is merged).
4. Unity (`Editor/WardShopsPass.cs`), **Athen Hill → Ward shops → North avenue: build assets**, **dry-run install**,
   **install (one-time)**, **install signs**, **verify saved scene**. After re-running 1–3: **Refresh models and
   materials** (re-imports, re-tunes materials and re-maps every prefab's material slots; see the evidence README for why).
5. `review_north.py -- <Model> [views=…]` (Cycles on the CPU) → `review/` source renders; not the game's render.

`north_kit.py` holds the continuous corrugated-sheet helper (the old strip method leaves slits visible from below).
Heavy media (`.blend`, review renders, logs) stays local per `.gitignore`.

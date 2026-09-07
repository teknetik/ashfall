# Character replacement — 2026-09-07

The replacement is a Blender audition awaiting export and actual-game QA.
It has improved anatomical topology, a fitted beard and hair, and layered
olive armour. It does **not** yet match the realism of
[`main_male_human_player_character.jpg`](../concept_art/main_male_human_player_character.jpg).
Earlier phase passes remain historical evidence for the earlier assets.

## Direction and authorization

The user rejected the primitive-looking player and explicitly authorized
external assets, primarily free, with inexpensive paid candidates available
for review. This overrides the guide's previous prohibition on marketplace
assets. The governing appearance is a realistic bearded adult man in worn,
segmented olive sci-fi armour with dark flexible joints and small cyan accents.
See the retained [direction update](art-direction-update.md). The supplied
concept remains a visual reference; no claim of ownership or redistribution
rights over that image is made here.

## Sources and actual use

The [MakeHuman manifest](../blender/sources/makehuman/source-manifest.json)
records downloaded pack URLs, SHA-256 hashes, original file paths and byte
counts. The [Poly Haven manifest](../blender/sources/polyhaven/source-manifest.json)
records each downloaded map and its hash. Raw source files and original
licence headers are retained under `blender/sources/`; generated geometry,
material changes and runtime GLBs are derivatives of those sources.

| Source | Use in the replacement | Licence evidence |
| --- | --- | --- |
| MakeHuman Community / MPFB 2.0.17 | Human mesh, anatomical targets, `game_engine` rig and weights; system `middleage_caucasian_male` diffuse skin, low-poly eyes and eyebrow001 cards | Core graphical assets are CC0; MPFB add-on code is GPLv3. [Primary licence](https://static.makehumancommunity.org/about/license.html), [system pack](https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html), [versioned add-on source](https://github.com/makehumancommunity/mpfb2/tree/v2.0.17) |
| grinsegold — Beard Sigmund WIP | Fitted, recoloured beard; original base geometry is 878 triangles | Current official [Bodyparts 05 pack](https://static.makehumancommunity.org/assets/assetpacks/bodyparts05.html) and retained `packs/bodyparts05.json` both identify this asset as CC0. [Author's asset entry](https://www.makehumancommunity.org/node/877) |
| Elvaerwyn — Grump hair | Fitted to the colonist, crest reduced, recoloured dark brown, retopology reduced through Blender decimation, materials adapted for export | CC-BY in both the original `.mhclo` header and current [Hair 02 pack](https://static.makehumancommunity.org/assets/assetpacks/hair02.html). [Author's asset entry](https://www.makehumancommunity.org/node/2796). The source does not supply a CC-BY version. |
| Mindfront — Aksel skin | **Normal map only**, `Aksel_Skin_NRM.png`, at strength **0.22**. The bruised/scarred diffuse albedo was rejected; the Aksel specular map is not used in the current material script. | CC0 in the [Skins 02 pack](https://static.makehumancommunity.org/assets/assetpacks/skins02.html) and retained pack metadata. [Author's asset entry](https://www.makehumancommunity.org/node/850) |
| Poly Haven — Blue Metal Plate; Fabric Leather 01 | Blue Metal Plate diffuse feeds a neutral wear bake; its normal map adds shallow metal detail. The current metal roughness is a constant, although the source roughness map is retained. Fabric Leather 01 supplies normal and roughness detail for the dark suit/gear; its downloaded diffuse is not currently connected. | [Blue Metal Plate](https://polyhaven.com/a/blue_metal_plate), [Fabric Leather 01](https://polyhaven.com/a/fabric_leather_01), [CC0 asset licence](https://polyhaven.com/license) |

The Sigmund `.mhclo` retains an older MakeClothes-generated `AGPL3` header.
This conflicts with the current official pack's per-asset CC0 declaration.
The project records both, uses the current official CC0 declaration as its
sourcing basis, and does not rewrite or conceal the older header. This is
provenance evidence, not a claim that the original header never existed.

RehmanPolanski's CC0 Viking beard and moustache remain in the source archive
as rejected auditions. They are not the selected beard. No purchased model
has been incorporated. The armour, collar, straps, pouches, boots and cyan
details are original Blender geometry authored for this project.

The distributable [third-party notice](../public/assets/THIRD_PARTY_LICENSES.md)
contains the hair attribution and links. The release needs a visible route
to that notice from the README or game credits; this documentation task does
not add or verify a runtime credits control.

## Reproduction and review status

The authoring stages are `12_character_audition.py` for the fitted base,
`13_colonist_armour.py` for the armour, `14_colonist_animation.py` for the
four movement/dialogue clips, `16_colonist_materials.py` for PBR materials,
and `15_colonist_optimize.py` for measured reduction and export preparation.
Blender MCP executes these stages. Fitting is performed in the rest pose;
the source body and its derived optimized output remain distinct.

The reviewed evidence is
[`09_materials_full.png`](../blender/previews/character-replacement/09_materials_full.png),
[`09_materials_portrait.png`](../blender/previews/character-replacement/09_materials_portrait.png)
and [`11_optimized_portrait.png`](../blender/previews/character-replacement/11_optimized_portrait.png).
Plate faceting is reduced, bevels and panel seams are readable, and the suit
has material variation. The face remains smoother and less rugged than the
reference; the beard has a sharply drawn edge, the swept hair remains a large
solid mass, and the armour's major plates are still broad and simplified.

Frame 11 loses the strong eyebrows visible in frame 09. The next revision of
stage 15 retains the eyebrow cards, but that code change requires a fresh
render. Neither that pending correction nor a successful export establishes
visual acceptance. The archived optimization report is an intermediate
snapshot, not certification of the final GLB's skin weights or frame budget.

Remaining evidence must come from the imported asset: close-up comparison
against the supplied concept, idle/walk/run/talk playback, feet and hand
alignment, skin/eye/hair alpha and normal-map rendering, and native 1080p
performance with all eight actors. Preserve the controller and collider
behaviour, the 250k rendered-triangle/80-draw limits, and the frame-rate gate.

## Optional paid candidate — not purchased

[Base Male And Sci-Fi Game Character Starter](https://superhivemarket.com/products/base-male-and-sci-fi-game-character-starter)
by **Aarón Hernández** was listed at **US$24.99** when checked on 2026-09-07.
The listing describes a rigged Blender character, 4k photogrammetry skin and
low-poly beard/hair cards. Clothing beyond basic underwear is excluded; its
hairstyle would also need adaptation. It is a possible human-base quality
upgrade, not a complete match for the armour reference.

No purchase, paid download or import has occurred; this candidate is pending
user review. The listed
[Royalty Free licence](https://superhivemarket.com/page/royalty-free-license)
permits commercial use and restricts redistribution or repackaging of the
purchased product itself. This record does not equate incorporation in a game
with resale of the source asset, or assert a WebGL encryption requirement.
Any remaining distribution question can be clarified with the creator if the
candidate is selected. The current free asset path continues independently.

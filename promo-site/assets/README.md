# Ashfall promo-site assets

Owner: designer (Kanban t_daeaf5d1), 1 Oct 2026. The authoritative per-asset record is `manifest.json`. It holds the web filenames, sizes, SHA-256 hashes, alt text, captions, visible labels, site role, spoiler notes and provenance for each asset.

## Layout

| Path | Contents |
| --- | --- |
| `manifest.json` | Asset manifest consumed by the website. |
| `originals/` | Byte-identical copies of the selected sources (hash-verified). Sources were never modified. |
| `web/` | Optimised derivatives: `<id>-<width>.avif` (q55), `.webp` (q80), `.jpg` (q82 progressive), stripped sRGB. |
| `generation/` | The Codex ImageGen run: `<id>.request.md` (the exact request fed to Codex), `<id>-prompt.md` (the exact image prompt that Codex saved), `<id>.png` (the original output), `logs/` (full Codex transcripts with start and finish times), `prompts.json`, `provenance.json`, `run_all.sh`. |
| `tools/selection.json` | Hand-written selection: ids, sources, alt text, labels and roles. |
| `tools/build_assets.py` | Rebuilds `originals/`, `web/` and `manifest.json` from the selection. Uses ImageMagick 7 and can be re-run. |
| `review/web-contact-sheet.jpg` | Decoded AVIF derivatives, used to check that the encodes look right. |

## Generated concept art (Codex ImageGen)

- Route: standalone `codex exec --sandbox workspace-write` (codex-cli 0.156.1, model gpt-6-sol). Each run invoked the `$imagegen` skill, which calls the built-in `image_gen` tool. That tool does not disclose the underlying image model.
- No other generator, fallback or placeholder was used.
- All six jobs ran in parallel from 13:10:08 BST on 1 Oct 2026. Finish times and Codex session ids are in `generation/provenance.json`.
- Every saved PNG is SHA-256-identical to its raw output under `~/.codex/generated_images/<session>/`.
- `ashfall-bleached-flats-caravan`: Codex exited with code 1 because of a model-capacity error on its final reporting turn. This happened after the image had been generated and copied and the prompt had been saved. The image itself is verified.
- Every image was inspected visually at full size, with close crops of hands, anatomy and lettering. None has text, logos or watermarks. The anatomy is acceptable for key art, and the caravan beasts and droids have the right number of legs.

| id | Subject | Website role |
| --- | --- | --- |
| ashfall-ward-hero | Ward at golden hour: the tree on the hill, hydroponic domes, the market, a cargo droid and a dormant ring gate | Hero (left third is clear for text) |
| ashfall-nano-infirmary-awakening | Karaveen doctors and a bandaged survivor; the wrist Lattice boots up | Opening chapter |
| ashfall-companion-recovery | A battered robot drags its splinted partner on a sled toward an outpost at dusk | Companions & recovery |
| ashfall-first-signal-node | A scavenger raises the wrist device; a feral giant halts; a ring node flickers | Machines (teaser) |
| ashfall-bleached-flats-caravan | Karaveen caravan, orbital wreckage, the Fallen Spire | Atlas (planned region) |
| ashfall-verdant-fold-station | Jungle valley with an overgrown research station; an explorer with a drone | Atlas (planned region) |

## Existing art selected

- `tir-world-map`: `concept_art/tir-map.png` (born 28 Sep 2026; generator not recorded). Labelled as a concept map.
- `ward-vanguard-hall-concept`: Carl accepted this target image on 30 Sep (`art/vanguard_hall_20260930/concept/ACCEPTED.md`).
- `outer-berms-depot-concept`: generated with gpt-image-1 on 27 Sep. The prompt is in the source folder's `prompts.json`.
- `build-ward-hill-20261001`: native development-build lookbook capture. `lookbook.json` gives utc 2026-10-01T10:47:45Z and the SHA-256 matches.
- `build-field-pack-20261001`: Obsidian paste in the vault, `Pasted image 20261001102337.png`. The paste timestamp equals the file's birth time.

Both build captures show the "Development Build" mark and legacy HUD names (Free Column / Athen Hill). They must keep the `IN BUILD · 1 OCT 2026` label.

## Not available or not used

- The original concept note embeds `Generated image 1/2/3/4 1/5.png`. Neither the vault nor the whole filesystem contains files with those names, so they could not be inspected or used.
- Pre-1 Oct screenshots and the 7 Sep browser-era refs/concept frames were excluded as obsolete.
- `hall_district` street concept and the West Gate concept were left out of the original pack (unaccepted shop signs; lettering). Both were added on 1 Oct for the /development concept-to-build pairs, captioned as concepts whose signs were not adopted / as a generated reference (next section).

## Added for the /development page (1 Oct 2026, Claude Code session)

19 build captures from the final 1 Oct lookbook (`unity/evidence/combined/20261001/final/lookbook-p0*/`, each SHA-256 checked against its `lookbook.json`; 13:00 and 20:50 in-game) and four concepts: `ward-west-gate-concept`, `ward-hall-street-concept`, `karaveen-stall-produce-concept`, `karaveen-stall-artisan-concept` (Codex sheets dated 10 Sep by filename). Added through `tools/selection.json` and `tools/build_assets.py`; the original 11 assets are unchanged.

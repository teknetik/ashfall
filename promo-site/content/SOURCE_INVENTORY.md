# Ashfall promo site — source inventory (INTERNAL, contains spoilers)

Prepared 1 October 2026 for Kanban task t_ecf7e316 (content lane). This file is internal. It is NOT for
publication: sections 5 and 6 name the story's twists so that downstream workers know what to keep out.
Public copy lives in `WEBSITE_COPY.md`.

Read-only discipline: no Obsidian note, game file or Unity asset was modified. Everything below was read
in full with line-numbered reads; the hashes record the exact versions used.

---

## 1. Verified vault and completeness check

Vault: `/home/teknetik/Documents/teknetik` (verified; the stale `/home/teknetik/Documents/Personal` was not
used — `/home/teknetik/Documents` contains only `Codex` and `teknetik`).

Recursive listing of `/home/teknetik/Documents/teknetik/AI/Ashfall` (`find . -type f`) returns exactly six
files, all markdown, no subfolders and no attachments:

| # | Exact filename (leading `#` preserved) | Lines | Bytes | Modified (BST) | SHA-256 (first 16) | Read |
|---|---|---|---|---|---|---|
| 1 | `# Ashfall - Core Narrative and Gameplay Vision.md` | 940 | 24,821 | 2026-10-01 11:36 | `3cbf360befb46045` | full, L1–940 |
| 2 | `# Death - Recovery and Robot Companion Systems.md` | 1,051 | 20,671 | 2026-10-01 12:33 | `b69477b72d9a1e5e` | full, L1–1051 |
| 3 | `Concept - Ashfall Protocol.md` | 561 | 26,853 | 2026-09-28 20:39 | `ee2a9c9555c08849` | full, L1–561 |
| 4 | `Phase 3 improvs.md` | 1 | 127 | 2026-10-01 11:07 | `8fbdd82fac5a11aa` | full |
| 5 | `Core Content.md` | 13 | 379 | 2026-07-30 16:30 | `5a74d2081dacf349` | full |
| 6 | `Improvements.md` | 58 | 2,131 | 2026-07-30 15:34 | `3e97e126ca668192` | full |

Repository sources also read in full:

| File | Lines | Modified | SHA-256 (first 16) | Role |
|---|---|---|---|---|
| `/home/teknetik/code/ao2/lore.md` | 78 | 2026-09-08 15:08 | `a43103f6d7b9fba8` | Older canonical setting draft |
| `/home/teknetik/code/ao2/AGENTS.md` | 391 | 2026-09-30 23:18 | `b1dda6775b01db93` | Production guide; current-build inventory (§3) |
| `/home/teknetik/code/ao2/promo-site/PROJECT_BRIEF.md` | 24 | 2026-10-01 | — | Site brief |
| `/home/teknetik/code/ao2/promo-site/design/DESIGN.md` | 384 | 2026-10-01 | — | Sibling design spec (IA §4, spoiler policy §9) |

Embedded images: note 3 embeds `Generated image 1.png`, `Generated image 2.png`, `Generated image 3.png`,
`Generated image 4 1.png`, `Generated image 5.png` (and `lore.md` additionally references `Generated image 6.png`
in a comment). `find /home/teknetik/Documents/teknetik -iname 'Generated image*'` returns nothing; the design lane
(t_daeaf5d1, `assets/manifest.json` notes) independently searched the whole filesystem with the same result.
They cannot be inspected and must not be described or reconstructed. Site art comes from the design lane's
manifest instead.

Result: 6 of 6 notes read completely; 0 unreadable; 5 embedded images missing on disk (recorded, not guessed).

---

## 2. What each source is

1. **`# Ashfall - Core Narrative and Gameplay Vision.md`** (newest narrative, 1 Oct 11:36). The requested
   vision. Premise; crash opening; Karaveen rescue; nano-infirmary; neural + ocular implants + wrist device =
   the Lattice; diegetic HUD boot; Lattice Capacity (NCU-like); assistant that only knows what you discover;
   classless attributes (STR/AGI/END/INT/PER/RES, Presence optional) with trickle-down into skills; implant
   slots; five-tab equipment UI; recipe-owned weapon mod slots; schematic vs skill crafting; reverse
   engineering; Outer Berms threats; the first signal; Ghost Network; robot companions and robot progression;
   assisted fabrication; deeper mystery and twist; central relationship; intended player journey.
2. **`# Death - Recovery and Robot Companion Systems.md`** (newest, 1 Oct 12:33). Incapacitation instead of
   death; the Anchor emergency system; companion emergency assessment and seven outcomes; field resuscitation;
   persistent injuries; medical facility hierarchy (field / outpost clinic / town hospital / Ward
   nano-infirmary); equipment recovery and salvage priorities; Karaveen recovery fee; companion insurance tiers
   and specialisations (Medical/Cargo/Combat/Engineering); companion damage moment; emergency neural support;
   Lattice sync points as diegetic saves; Lattice Jacks as fast travel the player rebuilds (six network stages);
   hidden narrative function (spoiler); theme ladder; optional Recovery vs Permadeath footnote.
3. **`Concept - Ashfall Protocol.md`** (28 Sep). Expanded world bible. Tir, Ward, Quantum Nano Tubes,
   Karaveen, Wardens (prose identical to lore.md) plus a much expanded Outer Berms and the whole wider-world
   atlas: 21 regions/seas across 8 macro-areas plus "The World Between Regions".
4. **`Phase 3 improvs.md`** (1 Oct). One line: the tutorial mission should send the player into a building to
   craft the weapon — the first walk-in building. Design intent only.
5. **`Core Content.md`** (30 Jul). Fragment: Quantum Tube node tiers (core free in big hubs / branch with small
   credit cost / leaf personal / possible personal short-range transporter) and an open question about a
   nano-based currency. Tentative.
6. **`Improvements.md`** (30 Jul). Checklist from the retired browser/MMO-style prototype era (mobs, DB reset,
   chat shortcut, NPC AI dialogue, loot windows, "Implement Ashfall version of NCU"). Ticked boxes describe that
   historical prototype; they are NOT evidence of the current Unity build. Useful only as intent signals
   (NCU-style capacity, implant/worn slots, secondary weapon slot, NPCs that remember your gear, ambient NPC
   movement, survival section still empty).

---

## 3. Source precedence used for website copy

Per PROJECT_BRIEF ("newer narrative notes expand and may supersede older repository lore") and AGENTS.md §1
(user's latest explicit instructions first):

1. Carl's latest instructions (PROJECT_BRIEF, 1 Oct).
2. Newest vision notes: `# Death - Recovery…` and `# Ashfall - Core Narrative…` (1 Oct). Requested vision —
   they define what the game is meant to become, not what exists.
3. `Concept - Ashfall Protocol.md` (28 Sep) — supersedes `lore.md` where they differ (its Outer Berms text is
   the newer, longer version) and is the only source for the atlas.
4. `lore.md` (8 Sep) — still canon for anything the newer notes do not contradict (Wardens, Great Rebuild
   framing).
5. `Phase 3 improvs.md`, `Core Content.md` — tentative intent, label as "exploring" or omit.
6. `Improvements.md` — historical; never used as shipped proof.

For **what is actually in the current build**, the only source is AGENTS.md §2–§3 (updated 28–30 Sep), which
itself says implementation status lives in the saved Unity scene. This content task did not run or inspect the
game (forbidden by the brief), so in-build statements are phrased as "the current development build includes…"
and cite AGENTS.md. Several 30 Sep art passes are marked there "Not yet accepted by Carl"; copy does not
present those as final art.

---

## 4. Conflicts between sources and how the copy resolves them

| # | Topic | Older position | Newer position | Resolution in public copy |
|---|---|---|---|---|
| C1 | Why Tir was cut off | lore.md / concept note: uncertain — forgotten, quarantined for the rogue AI problem, or overtaken by bigger catastrophes. AGENTS.md: "remains unknown; do not invent a definitive answer". | Core Narrative: the accepted history is wrong; Tir was deliberately disconnected (major twist). | Newer note supersedes as story vision, but it is a spoiler. Public copy keeps the *accepted history* and the open question ("the accepted history says…", "not everyone believes the story"). Never states the answer. Consistent with both AGENTS.md and the brief. |
| C2 | Player's start | lore.md: "You wake in the crumbling oasis-city of Ward." | Crash on Tir, fragmented memories, Karaveen recover the sole survivor, nano-infirmary implants, first Lattice boot. | Crash opening foregrounded. Compatible: the Death note names "The Ward Nano-Infirmary", so you wake *in Ward*. Copy: Karaveen recover you from the wreck and bring you to the nano-infirmary in Ward. |
| C3 | Who the Karaveen are | Concept/lore: nomadic caravan traders, tradition kept alive after the Tubes; lifeline to unconnected outposts. | Core Narrative: a culture that survives by scavenging, repair, trade and adaptation; "the Karaveen settlement known as The Ward"; Karaveen doctors; Death note: Karaveen recovery network and contract. | Merged: a people of the road — traders, salvagers, repairers — whose caravans, doctors and recovery teams reach where the Tubes don't. Copy avoids calling Ward a Karaveen-only city (lore/AGENTS: Ward is the oasis city, defended by the Wardens); it says the Karaveen are at the heart of Ward's survival and bring you there. Flag for Carl. |
| C4 | Quantum Tubes & passenger travel | Concept/lore: matter disassembly/reassembly for *goods*; core restored in the Great Rebuild, many branch nodes woke on their own. AGENTS.md: do not turn goods-only Tube lore into confirmed passenger transport. | Death note: most transport terminals dormant for decades; the protagonist's implants reawaken legacy nodes ("Lattice Jacks") as fast travel the player rebuilds. Core Narrative: Tube connections failed in the collapse. | The newest vision explicitly makes reactivated legacy nodes the player's fast travel, so it is presented — but labelled PLANNED and described as something your implants make possible, not as general public passenger service. Goods-network restoration stays as world history. Mechanism of human transit is not explained. Flag the AGENTS.md tension for Carl. |
| C5 | Name of the city | "Ward" (lore, AGENTS) | "The Ward" (both 1 Oct notes) | Use "Ward" in running prose and "the Ward nano-infirmary" where natural; both read fine. |
| C6 | Outer Berms text | lore.md short version (neutral ground in name only, "few return") + `Generated image 6.png` comment | Concept note: long version (old industrial district, territorial feral clusters, dog/rabbit/serpent analogues, raiders on Karaveen roads, young Wardens' first patrols). Core Narrative adds the same three threat types. | Concept-note version used (newer, richer). |
| C7 | Protagonist identity/pronoun | — | Core Narrative: identity unknown, no gender. Death note: "saved *his* life… *he* provides them…" | Gender-neutral "you" throughout. Flag. |
| C8 | Anchor vs Lattice | — | Death note introduces "the Anchor" (vital monitoring, emergency beacon, salvage priority config) without defining its hardware relationship to the Lattice. | Copy describes the Anchor only by function ("the Anchor, an emergency system that watches over your body"). No invented hardware. |
| C9 | "Lattice Jack" meaning | Build (AGENTS.md §2): "Lattice Jack" is an existing implementation name; "Use the Lattice transition and sector overlay"; Ring Gate keeps an offline response. | Death note: Lattice Jacks = reawakened transport nodes. | Public: Jacks presented as the planned rebuildable network. "In build" status rail may mention only that the district build has an early Lattice transition/sector overlay and an offline Ring Gate. |
| C10 | Scrap pistol mod slots | — | Core Narrative example: crude scrap pistol supports barrel and grip only. | AGENTS.md: build's scrap pistol has grip/barrel/**cell** mods. Copy uses the build fact where talking about the build and keeps the note's slot examples as illustrations of the principle ("for example"). |
| C11 | Merchant / NPC names | — | Core Narrative example: "Merchant Kess". | Build has Mira, Torr, Vex, Linn, Ossa, Depot Foreman (AGENTS). AGENTS says names in the build are not extra canon and a naming pass is pending. Copy uses Kess only inside the clearly illustrative assistant example; no build NPC names on the public site. |
| C12 | Scope promises | lore.md Ward blurb: "rebuild and expand the settlement, master… intense FPS combat". | AGENTS.md: survival, settlement rebuilding, nanotech weapons and FPS combat are future milestones, not implemented; multiplayer/vehicles/extra regions not current tasks. | Settlement rebuilding mentioned only as long-term vision. No multiplayer claims at all. |
| C13 | Currency / node tiers | — | Core Content: tentative nano-currency idea and node tiers. Death note uses "credits". | Credits mentioned only in the recovery-fee example as illustrative. Nano currency and node tiers marked "exploring" in FAQ, not stated. |
| C14 | Wardens | lore/concept: heavily augmented militia carrying sandboxed AI sub-routines. | Not mentioned in 1 Oct notes. | Retained (no conflict). Note: Wardens carrying "sandboxed fragments of loyal industrial code" is thematically adjacent to the twist; copy mentions augmentation but does not dwell on AI fragments. |
| C15 | Region named Ashfall | — | Concept note: "Ashfall Basin" is a volcanic region far north-east of Ward, while the game/site is titled Ashfall and the concept note is "Ashfall Protocol". | Basin described in atlas as-is. Copy does not invent a link between title and basin. Flag for Carl as a thematic hook worth deciding. |

---

## 5. Spoiler register (keep OUT of all public copy, alt text, meta, OG tags, HTML comments)

Aligned with DESIGN.md §9.

| Spoiler | Source |
|---|---|
| Tir was deliberately disconnected/quarantined; "the reason is buried inside the player" | Core Narrative L24–30, L724–746 |
| The Ghost Network as a surviving, shattered planetary intelligence (name and full explanation) | Core Narrative L520–562 |
| "AUTHORITY NODE DETECTED", machines kneeling, doors/permissions auto-granted | Core Narrative L646–684 |
| The assistant is a surviving fragment of Tir's planetary AI; Karaveen unknowingly installed it | Core Narrative L688–720 |
| True collapse: contradictory corporate directives fragmenting the intelligence | Core Narrative L724–798 |
| Restoring the companion may restore what the galaxy tried to contain | Core Narrative L832–838 |
| "They aren't trying to contact me… They're trying to rejoin me." | Core Narrative L842–862 |
| Lattice Jacks are reconnecting the nervous system of something larger | Death note L805–836 |
| Route 00-Ω / "AUTHORITY LEVEL: OBSOLETE" (implies the above) | Death note L788–799 |
| Ending question: "what happens if I reconnect it?"; the ending's aim, "the true collapse of Tir" | Core Narrative L928–940 |

Allowed teasers (DESIGN §9): the crash; implants; the Lattice and an assistant inside it; "the accepted history
says"; feral machines; the first-signal moment up to "the machines are detecting the Lattice"; machines
hesitating and watching; Jacks as fast travel you rebuild; the relationship framed as "two incomplete beings"
(the assistant "does not know what it was" is acceptable — it does not say what it is). The "IDENTITY CONFLICT"
glitch is used once as a hook; it does not reveal the answer.

---

## 6. Design vision vs current build (honesty ledger)

Nothing from the Obsidian notes is shipped proof. The only current-build statements permitted come from
AGENTS.md (28–30 Sep 2026), unverified by this content task:

IN THE CURRENT DEVELOPMENT BUILD (native Linux, Unity, one district — per AGENTS.md §2–§3):
- Walkable Ward district: West Gate, avenue, hill stairs, oasis hero tree, Vanguard Hall, shops (several art
  passes from 30 Sep not yet accepted by Carl).
- Four talking NPCs with branching dialogue/objectives; ambient walkers and a yard mechanic.
- Trading at a general store (flask purchase, scrap sale).
- An early Lattice transition and sector overlay; South Ring Gate present with an offline response.
- Outer Berms loop: scrap pistol with grip/barrel/cell mods, refined components, seeded loot with bad-luck
  protection, salvage caches and scrap heaps, an elite depot enemy, five field orders, shop supplies/buy parts/
  sell salvage, versioned save with Continue.
- Corner HUD, hotbar with six working actions; music/ambience/spatial audio; reduced-motion option.

PLANNED / DESIGN VISION (not implemented as far as sources show): crash opening and nano-infirmary sequence;
diegetic Lattice boot; Lattice Capacity and modules; knowledge-as-loot assistant; six-attribute trickle-down
system and skills; implants (8 locations); five-tab equipment UI; armour slots; plasma rifles and advanced weapon
recipes; schematics/reverse engineering; robot companions and their progression; assisted fabrication; the Anchor;
incapacitation outcomes; persistent injuries; medical hierarchy; salvage priorities; recovery fees; Lattice sync
points; Lattice Jack network; Recovery/Permadeath choice; all regions beyond Ward and the Outer Berms; settlement
rebuilding; wildlife; bandits as a system; the tutorial walk-in crafting building.

UPDATE 1 Oct 2026 (Claude Code session, release gate Q6): the merged 1 Oct build adds an early character sheet:
six attributes, skills, 8 implant and 6 armour slots, a five-tab equipment screen (Primary, Secondary, Stats,
Implants, Armour), loadouts and carry weight (`unity/CHARACTER_PROGRESSION.md`, `CharacterCatalog.asset`), and the
Warden training range. Those early forms are now IN BUILD; the full trickle-down progression and implant effects as
designed stay PLANNED. A walk-in Salvage shop with a workbench is in testing (not in the 1 Oct test build).
The newer note `Consciousness Transfer Arc.md` (moved into AI/Ashfall on 1 Oct) is not used in public copy; it
contains major spoilers and its rows are not yet in the §5 register.

NOT CLAIMED ANYWHERE: multiplayer, in-game accounts, vehicles, launch date, price, platform beyond the current
native Linux development build, download, test sign-up for build access, testimonials.

---

## 7. Thematic hooks inventory (for copy, art direction and future discussion topics)

- A company world that "was never intended to be self-sufficient" learning to be.
- Machines as civilisational trauma: robots still obeying orders for customers dead for centuries.
- Interface as body: the HUD is literally your rebuilt eyes; the UI grows as you heal.
- Information as loot; an assistant honest about what it doesn't know.
- No classes — a build is a body, a toolkit and a team.
- Repair over conquest: Wardens "the wall that has never been allowed to fall"; companions earned by repair and
  handshake, not domination.
- Failure as story: "A disastrous battle should sometimes become the beginning of another story."
- The robot that "dragged you nearly four kilometres" and only reports RECOVERY OBJECTIVE COMPLETED.
- Fast travel you physically rebuild.
- Water as power (Dune Wastes); nodes as power (World Between Regions).
- The Dominion: "the Fall never truly ended. It simply became organised."
- Pre-human ruins under the Shattered Spine; non-human structures in the Sundered Delta; impossible-depth
  structures in the Cobalt Deep; energy readings in Viridian trenches; something huge under the Salt Expanse and
  Stormreach Sea — a world full of unanswered questions independent of the main twist.
- Ember Crown "slowly awakening" — geologists say superstition; "their evacuation plans suggest otherwise".
- The Fallen Spire: an orbital elevator that ends in mid-air.
- Sunscar Reach's defences built against an enemy no record names.
- Possible sapience among Verdant Fold animals; organised amphibians in the Delta.

---

## 8. Open questions for Carl (do not block publication)

1. Is Ward a Karaveen city, or a Warden-defended oasis the Karaveen serve? (C3)
2. Should Lattice Jacks carry people, given goods-only Tube lore? (C4)
3. What is the Anchor physically? (C8)
4. Is there an intended link between the title "Ashfall" and the Ashfall Basin / "Ashfall Protocol"? (C15)
5. Should the site ever carry an opt-in "designer's notes (spoilers)" section? Default: no (DESIGN §9).
6. The missing `Generated image 1–6.png` files — if they exist elsewhere, the design lane can add them.

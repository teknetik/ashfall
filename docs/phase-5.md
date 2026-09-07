# Phase 5 — conversations, trading and local travel

**Functional acceptance passed on 2026-09-07. Visual acceptance remains open.**
The user rejected the current character graphics; this phase does not approve
their appearance or complete the game. Character replacement follows
[the updated art direction](art-direction-update.md). The results below describe
the preserved production build tested before that replacement.

## Behavior and source ownership

`src/game.ts` owns the visit state, dialogue selection, inventory actions, local
log and progress. Its states are boot, play, dialogue, shop, grid, paused and
error. Conversation/shop/travel panels stop player movement and camera input;
the town continues animating. Pause freezes the player and NPC bone poses and
ambient positions. Escape closes a panel or resumes exploration and restores
canvas focus. Movement keys are cleared at those transitions.

`src/dialogue.ts` contains seven original nodes for Mira, Torr, Vex and Linn.
Every node has exactly two choices. Mira opens Basic General; the other three
colonists have one optional lore follow-up. Unknown nodes fail explicitly.
Dialogue data is immutable, with no quests, accounts or network persistence.

`src/shop.ts` starts a local session with 25 credits and one Scrap Coil.
Transactions transfer exactly one item and only successful trades advance
the purchase/sale counters. Invalid identifiers, insufficient funds and empty
inventory cannot alter balances. Catalogue entries and snapshots are immutable.

| Item | Buy | Sell |
| --- | ---: | ---: |
| Water Flask | 4 | 2 |
| Medkit | 9 | 4 |
| Scrap Coil | 2 | 1 |

`src/travel.ts` supplies a 1.25-second Lattice connection and three local nodes:
Crosswind Reach, Drywater Works and Beacon Dunes. Selecting a node logs a link
message without moving the capsule or loading a second zone. The Ring Gate
reports its offline destination. The visit completes after reaching the hill,
meeting all four colonists, buying a flask, selling scrap and selecting a node.

`src/ui.ts`, `src/ui-icons.ts` and `src/style.css` provide original thin-edged
MMO chrome, six quick slots, vitality/nano indicators, an inventory panel, city
notes, chat, interaction brackets, dialogue, shop and lattice panels. Item icons
are original inline SVG. UI controls dispatch the same Game actions as keyboard
input in `src/input.ts`. Read-only diagnostics in `src/debug.ts` expose story,
inventory, dialogue, grid, interactions and logs. Survey controls are absent
from the normal production URL.

Integration review fixed three input/layout defects: keyboard slots 5/6 now
share the click dispatcher; a trade that disables its focused control restores
focus to an enabled control; and mobile modal columns/panel widths stay inside
the viewport. The phone Notes slot now reveals its content while retaining the
compact header.

## Verification and evidence

The final [production report](../tools/phase5-support/runs/2026-09-07T11-07-20.844Z-31068/report.json)
passes on the normal `http://127.0.0.1:4173` URL with headed Chromium/Metal:

- Real E interactions with all four NPCs; two-choice greetings/follow-ups,
  keyboard selection, focus trapping, Escape and stationary modal movement.
- A flask purchase, sale of the starting coil, coil buy/sell, disabled empty
  sales and unaffordable purchases, and the complete visit objective.
- All six keyboard slots, visible phone inventory/Notes menus, a 1.25-second
  Lattice transition, all three node selections and the Ring Gate offline line.
- 120.06 fps at 1920×1080 on Apple M4 Max, 57 draws and 224,596 rendered
  triangles with eight character instances; zero browser errors.
- 390×844 gameplay/dialogue/shop/grid fit and actual touch interaction. The
  corrected Lattice panel spans x=12 through x=378, within the 390px viewport.

The harness uses **ten recorded public `goto` teleports for interaction
fixtures**, plus real movement/rotation/input. It does not claim a new continuous
route. All 263 static collider definitions and controller settings exactly match
the earlier successful no-teleport Phase 3 route, preserving that evidence.

Additional [responsive checks](../tools/phase5-support/runs/2026-09-07T11-05-22.062Z-responsive/report.json)
cover gameplay, pause, dialogue, shop and grid at 1280×720, 768×1024 and 844×390.
These checks preceded only the phone Notes visibility selector; the final full
run verifies that selector at 390×844. Earlier failed runs and the exact mobile
overflow reproduction remain archived alongside the passing runs.

The [shop/dialogue model report](../tools/phase5-support/model-checks.json) covers
1,000 varied transaction attempts, exact-price zero balance, atomic failures,
invalid/prototype/non-finite IDs, immutable snapshots, independent sessions and
all seven linked dialogue nodes. The
[travel model report](../tools/phase5-support/travel-checks.json) covers exact
timing, invalid deltas/IDs, detached snapshots, optional reduced motion, 25
repeated sessions and resource disposal. OS motion-preference wiring is not
claimed by the model test.

Commands:

```sh
npm run build
npm run verify:models
npm run verify:travel
npm run verify:phase5
```

The package and lockfile version are 0.5.0. Production build passes. Vite still
reports the existing large JavaScript chunk warning (about 3.56 MB minified,
1.28 MB gzip); this phase did not change bundle partitioning. Native performance
is evidence for the reported machine, not an untested medium laptop. Audio,
character replacement and final beauty/ship acceptance remain separate work.

## Reference ledger

The inspected frozen UI target is `refs/08_ui_overlay.png`; original geometry
and the new character reference remain governed by the art-direction update.
Skill references are design/review guidance; browser reports above provide the
actual functional and fit evidence.

| Source in `threejs-game-ui-designer/` | Read | Failure |
| --- | --- | --- |
| `SKILL.md` | Yes | None |
| `references/ui-patterns.md` | Yes | None |
| `references/checklists/game-ui-quality.md` | Yes | None |
| `references/checklists/hud-readability.md` | Yes | None |
| `references/checklists/responsive-ui-fit.md` | Yes | None |
| `references/checklists/mobile-input.md` | Yes | None |

All required UI references were re-read during final review by both the UI owner
and integration reviewer. Reusable prompt templates were not applicable.

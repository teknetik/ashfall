# Reference UI acceptance · 8 September 2026

User target: `refs/ui_20260908/target.png`.

Implemented the reference's corner HUD, combined identity/vitals, live compass, field notes/progress diamonds, utility strip, illustrated six-slot equipment bar, local log, interaction hints and NPC markers. All existing dialogue, shop, inventory, lattice, pause/settings, notes and credits screens share the original bronze frame system. Native labels and named controls remain editable in UI Builder.

## Verification

- Final Linux development and release builds succeeded (`both-final.log`).
- Existing real-keyboard city-loop test passed: four conversations, choices, modal movement blocking, buy/sell balance and quantities, lattice links, completed objectives, inventory, notes, pause, audio/motion options, reset and credits.
- Illustrated hotbar mouse click reached its intended action and was detected as UI input.
- Native screenshots inspected at 1920×1080, 1280×720 and 1024×768. Geometry assertions confirm HUD frames stay inside the window and do not overlap; log viewport stays between its heading and footer; small-window type increases to 20 reference pixels.
- Credits header/footer remain fixed while body content scrolls. Scrollbars use the shared palette. Inactive HUD controls cannot receive modal focus.
- 17 native screen captures; no runtime exceptions, missing UI assets or stylesheet warnings in the final run.
- Native avenue sample: 318.0 fps on this host. Draw-call recorder returns zero/unavailable on this runtime; recorded triangle totals include repeated render passes and do not establish a unique-geometry budget.
- Release launch, real keyboard input and nonblank rendering passed; release correctly ignores the opt-in development QA flag.
- `git diff --check` passed.

## Delivery

Release: `unity/AthenHill/Builds/Linux/AthenHill.x86_64`.
Editable UI: `unity/AthenHill/Assets/AthenHill/UI/CityHUD.uxml`, `CityHUD.uss`, `Art/`.
Original SVG sources and generated item art/prompts: `refs/ui_20260908/`.
Font licence accompanies both builds. Unrelated scene, model and other existing work has been preserved.

Build reports also record the host's existing licensing/VBCS environment messages; both builds completed successfully with no C# or USS compilation failures. Native logs are clean of runtime exceptions.

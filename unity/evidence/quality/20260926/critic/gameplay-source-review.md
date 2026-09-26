# Read-only gameplay review — 26 September 2026

## Substantiated finding

**[P2] Persist the reduced-motion preference across launches.** `GameSession.ToggleReducedMotion()` (`Assets/AthenHill/Scripts/GameSession.cs:105`) only flips the in-memory `reducedMotion` field and raises `Changed`. The saved scene sets `reducedMotion: 0` (`Assets/AthenHill/Scenes/AthenHill.unity:149444`), while `GameSettings.Awake()` reads only Sound and Video preferences. No save/load path for reduced motion exists anywhere in the reviewed scripts. Consequently, enabling Reduced motion, quitting and launching again restores motion without the user's choice: the lattice tunnel resumes, atmosphere wind/dust animate again, and the reduced-motion clock-speed restriction is lost. Other exposed preferences such as mute, video settings and HUD placement persist.

This is deterministic from the save/load path, not a newly executed native reproduction. Suggested narrow repair: persist reduced motion in `GameSettings` under its existing normal/QA preference isolation, restore it before session presentation starts, and keep `GameSession.reducedMotion` synchronized for existing consumers. Keep the current wind, dust, tunnel and clock behavior. Verify both enabled and disabled preferences across restart using an isolated preference directory, plus the existing in-session reduced-motion check.

## Checked paths without a new defect finding

- `ShopModel.Trade` validates availability and calculates credits, quantity and transaction-count changes in checked locals before committing any of them. Failed unknown-item, insufficient-credit, empty-inventory and overflow paths leave state unchanged. Existing tests cover the central atomicity cases; this review did not execute Unity tests.
- `GameSession.SetState` disables the gameplay input map for modal states and blocks horizontal player motion. `GameInput.SetGameplay` clears look/jump state; the player consumes queued jump once. No concrete modal movement bypass was found in these source paths.
- Current catalog contains exactly three items and three destinations. Each current dialogue node contains two choices and existing next-node targets match the saved data. The fixed UI row assumptions therefore do not currently break this district; hypothetical future malformed data is not reported as a present defect.
- Confirmed video settings alone are written to disk; preview changes use an unscaled recovery deadline and revert on timeout. Existing native settings scripts include keyboard control, movement blocking, preview/revert and persistence checks. These old scripts are not proof of today's runtime.
- The saved catalog correctly instructs left-drag camera look. The unused `CityCatalog` field initializer still says right-drag, but current player-facing notes use the corrected saved asset; no current gameplay defect is claimed for that stale initializer.

Scope: source and serialized-data inspection only. Desktop lock prevented real-input native checks during this review. No source changes were made by the critic.

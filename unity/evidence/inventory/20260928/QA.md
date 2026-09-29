# QA — Unity native inventory interaction and visual quality

Date (UTC):   2026-09-28 07:49:34Z
Date (local): 2026-09-28 08:49:34 BST

Repo:   /home/teknetik/code/ao2
Branch: main
HEAD:   0b4496adf34d0eb01a6f5050cac1b163989ad923

Unity editor: /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity  (expected 6000.6.0f1)
Dev build:    /home/teknetik/code/ao2/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64

Scope:
- Verify the native Unity inventory UI (UI Toolkit): Tab opens/closes from Play; Esc closes details then inventory; does not open from Shop; grid/overview/details; keyboard+mouse; quantities after trade; small viewport; empty state; gameplay blocking.
- Evidence must be backed by real command outputs + screenshots/logs (no source-review-only pass).

Result summary:
- PASS: Native automated real-input acceptance run (Tab/Esc semantics, shop blocking, trade updates, 1280x720 smoke).
- PASS: Native hover preview (hover temporarily overrides selection; exit restores).
- PASS: Native empty state (selling starting scrap -> empty inventory view shows correct copy).
- PASS: Unity EditMode tests (full suite 70/70; InventoryTests 4/4).

---

1) Native acceptance run (real input via X11 xtest)
Command:
  ATHEN_INVENTORY_EVIDENCE=unity/evidence/inventory/20260928/native-qa-20260928T073511Z uv run --with python-xlib python unity/evidence/inventory/20260928/check_inventory.py
Observed stdout (report.json equivalent):
{
  "complete": true,
  "screenshots": [
    "inventory-1280x720-details-enter.png",
    "inventory-1280x720.png",
    "inventory-after-esc-details-closed.png",
    "inventory-after-trades.png",
    "inventory-before-tab-close.png",
    "inventory-details-enter.png",
    "inventory-details-shift-click.png",
    "inventory-initial.png",
    "play-1280x720.png",
    "play-avenue.png",
    "shop-after-trades.png",
    "shop-open.png"
  ],
  "finalState": "Play",
  "credits": 22,
  "quantities": {
    "water_flask": 1,
    "medkit": 0,
    "scrap_coil": 0
  }
}

Evidence:
  unity/evidence/inventory/20260928/native-qa-20260928T073511Z/
  Key screenshots:
    inventory-1280x720-details-enter.png, inventory-1280x720.png, inventory-after-esc-details-closed.png, inventory-after-trades.png, inventory-before-tab-close.png, inventory-details-enter.png, inventory-details-shift-click.png, inventory-initial.png, play-1280x720.png, play-avenue.png, shop-after-trades.png, shop-open.png
  Notes:
  - Visual: compact grid + overview; qty badge; footer hint text; details overlay is a separate subwindow w/ Close details; 1280x720 stacks overview below grid.
  - Logs: launcher.log captured; Player.log was not present in this run dir (see Remediation).

2) Native hover-preview run (2-item inventory)
Command:
  ATHEN_INVENTORY_EVIDENCE=unity/evidence/inventory/20260928/native-hover-qa-20260928T074700Z uv run --with python-xlib python unity/evidence/inventory/20260928/check_inventory_hover.py
Observed stdout:
{
  "complete": true,
  "screenshots": [
    "inventory-two-items-hover-exit.png",
    "inventory-two-items-hover-scrap.png",
    "inventory-two-items-initial.png",
    "shop-after-buy-0.png",
    "shop-before-hover-test.png"
  ],
  "finalState": "Inventory",
  "credits": 21,
  "quantities": {
    "water_flask": 1,
    "medkit": 0,
    "scrap_coil": 1
  }
}

Evidence:
  unity/evidence/inventory/20260928/native-hover-qa-20260928T074700Z/
  Screenshots:
    inventory-two-items-hover-exit.png, inventory-two-items-hover-scrap.png, inventory-two-items-initial.png, shop-after-buy-0.png, shop-before-hover-test.png
  Visual check (from screenshots):
  - Initial overview shows Water Flask; hover over Scrap Coil updates overview to Scrap Coil without changing selection; moving pointer away restores Water Flask overview.

3) Native empty-state run
Command:
  ATHEN_INVENTORY_EVIDENCE=unity/evidence/inventory/20260928/native-empty-qa-20260928T074811Z uv run --with python-xlib python unity/evidence/inventory/20260928/check_inventory_empty.py
Observed stdout:
{
  "complete": true,
  "screenshots": [
    "inventory-empty.png",
    "shop-after-sell-scrap.png",
    "shop-open.png"
  ],
  "finalState": "Inventory",
  "credits": 26,
  "quantities": {
    "water_flask": 0,
    "medkit": 0,
    "scrap_coil": 0
  }
}

Evidence:
  unity/evidence/inventory/20260928/native-empty-qa-20260928T074811Z/
  Visual check (inventory-empty.png):
  - Left content shows: "Your field pack is empty." / "Supplies you acquire will appear here."
  - Overview shows: "No item selected."

4) Unity EditMode tests
Command used (important: omit -quit; with -quit the editor exited before executing tests in this environment):
  /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity -batchmode -nographics -projectPath /home/teknetik/code/ao2/unity/AthenHill -runTests -testPlatform EditMode -testResults /home/teknetik/code/ao2/unity/evidence/inventory/20260928/tests/editmode-results-qa-nq-20260928T073759Z.xml -logFile /home/teknetik/code/ao2/unity/evidence/inventory/20260928/tests/editmode-qa-nq-20260928T073759Z.log

Results summary (from XML):
  overall: {'result': 'Passed', 'total': '70', 'passed': '70', 'failed': '0', 'skipped': '0', 'inconclusive': '0', 'duration': '212.8623664', 'start-time': '2026-09-28 07:38:14Z', 'end-time': '2026-09-28 07:41:47Z'}
  InventoryTests: {'result': 'Passed', 'testcasecount': '4', 'passed': '4', 'failed': '0', 'duration': '0.656299'}

Evidence:
  unity/evidence/inventory/20260928/tests/editmode-results-qa-nq-20260928T073759Z.xml
  unity/evidence/inventory/20260928/tests/editmode-qa-nq-20260928T073759Z.log

---

Pass/fail against requested behaviors:
- Tab opens inventory from Play: PASS (native_main automated run).
- Tab/Esc close behavior (details first, then inventory): PASS (native_main automated run).
- Other modals/startup unaffected: PARTIAL (EditMode test asserts ToggleInventory does nothing in MainMenu/Settings; native run confirms Shop blocks Tab. Dialogue/startup text-field edge cases not directly exercised in native run).
- Grid shows carried-only items; quantities update after trade: PASS (native_main; also verified by report quantities).
- Empty state from truly empty inventory: PASS (native_empty).
- Hover preview + focus preview: PASS (native_hover for hover; keyboard focus verified visually by focused tile cyan outline in screenshots).
- Shift+click and Enter open details; Esc closes details and returns focus: PASS (native_main screenshots + scripted flow).
- Small-screen layout (1280x720): PASS (native_main).
- Shop/hotbar + gameplay blocking: PASS/PARTIAL (Shop blocks Tab in native_main; player.Blocked toggling is covered in InventoryTests; manual free-walk while inventory open not performed).

Remediation / follow-ups:
- Player.log missing in native_main evidence dir (only launcher.log present). If needed, confirm whether Unity is honoring -logFile in the Linux dev build; consider writing logs to a unique path and verifying file creation after process exit.
- If we want stronger confidence on “Tab does not open from Dialogue / input fields / startup screens”, extend the native script to enter Dialogue/Settings and press Tab while those panels are focused, then assert state unchanged + capture screenshots.

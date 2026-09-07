import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { inspectGLB, inspectPixels, horizontalDistance, wrappedAngle } from './phase3-support/checks.mjs';

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node tools/verify-phase5.mjs [production URL]');
  console.log('Headed Chromium/Metal, default http://127.0.0.1:4173 without debug query. Does not build.');
  console.log('Tests dialogue, shop, modal input, hotbar, travel, story, GPU budgets and mobile fit. Public goto fixtures are recorded as teleports.');
  process.exit(0);
}
assert(args.length <= 1 && !args.some(value => value.startsWith('--')), 'Only an optional production URL is supported.');
const url = args[0] ?? process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:4173';
assert(['http:', 'https:'].includes(new URL(url).protocol) && !new URL(url).searchParams.has('debug'), 'Use a normal production URL without debug query.');
const stamp = `${new Date().toISOString().replaceAll(':', '-')}-${process.pid}`;
const relativeOutput = `tools/phase5-support/runs/${stamp}`;
const output = fileURLToPath(new URL(`./phase5-support/runs/${stamp}/`, import.meta.url));
await mkdir(output, { recursive: true });
const baselinePath = process.env.ATHEN_PHASE3_REPORT ?? fileURLToPath(new URL('./phase3-support/runs/2026-09-07T09-59-38.809Z-14868/report.json', import.meta.url));
const report = { url, output: relativeOutput, scope: 'Phase5 functional integration only; character appearance is explicitly NOT visually accepted.',
  inputMethod: 'Real keyboard/mouse/touch actions. Public goto is used only for recorded interaction fixtures; no private state mutation.',
  startedAt: new Date().toISOString(), errors: [], warnings: [], checks: [], assets: [], teleports: [], captures: [], layoutChecks: [],
  visualAcceptance: 'WITHHELD: the current character appearance was rejected and replacement work is separate.',
  limitations: ['Visual acceptance remains separate and is not implied by this run.', 'Historical continuous traversal is retained only if static collision/controller definitions match.',
    'Measured FPS applies to the reported native GPU; it does not certify an untested medium laptop.'] };
const started = Date.now(), jobs = [];
let browser, page;
const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, stable(value[key])])) : value;
const canonical = value => JSON.stringify(stable(value));
const quantity = (inventory, id) => inventory.items.find(item => item.id === id).quantity;

async function observe(target, label) {
  target.on('pageerror', error => report.errors.push(`${label} page: ${error.message}`));
  target.on('console', message => { if (message.type() === 'error') report.errors.push(`${label}: ${message.text()}`); else if (message.type() === 'warning') report.warnings.push(`${label}: ${message.text()}`); });
  target.on('requestfailed', request => report.errors.push(`${label} request: ${request.failure()?.errorText} ${request.url()}`));
  target.on('response', response => { if (response.status() >= 400) report.errors.push(`${label} HTTP ${response.status()}: ${response.url()}`); });
  await target.route(/\.glb(?:[?#]|$)/i, async route => {
    const job = (async () => { try {
      const response = await route.fetch(), body = await response.body();
      report.assets.push({ browser: label, url: route.request().url(), status: response.status(), ...(response.ok() ? inspectGLB(body) : {}) });
      await route.fulfill({ response, body });
    } catch (error) { report.errors.push(`${label} asset: ${error.message}`); await route.abort(); } })(); jobs.push(job); await job;
  });
}
async function boot(target) {
  await target.goto(url, { waitUntil: 'networkidle' });
  await target.waitForFunction(() => window.__ATHEN__ && window.__ATHEN__.state !== 'boot', null, { timeout: 45000 });
  await target.evaluate(() => window.__ATHEN__.ready);
  const identity = await target.evaluate(() => ({ phase: window.__ATHEN__.phase, version: window.__ATHEN__.version, state: window.__ATHEN__.state, error: window.__ATHEN__.error }));
  assert(identity.phase >= 5 && identity.state === 'play', JSON.stringify(identity));
  assert.equal(await target.locator('.instrumentation').count(), 0, 'Normal production hides survey instrumentation.');
  return identity;
}
async function snapshot(target = page) {
  return target.evaluate(() => ({ state: window.__ATHEN__.state, player: window.__ATHEN__.player, input: window.__ATHEN__.input,
    story: window.__ATHEN__.story, inventory: window.__ATHEN__.inventory, dialogue: window.__ATHEN__.dialogue, grid: window.__ATHEN__.grid,
    interaction: window.__ATHEN__.interaction, logs: window.__ATHEN__.logs, npcs: window.__ATHEN__.npcs,
    playerAnimation: window.__ATHEN__.playerAnimation, renderer: window.__ATHEN__.renderer, error: window.__ATHEN__.error }));
}
async function release(target = page) { for (const key of ['w', 'a', 's', 'd', 'Shift', 'ArrowUp']) await target.keyboard.up(key); }
async function capture(target, name) {
  const pixels = inspectPixels(await target.locator('canvas').screenshot());
  const path = `${relativeOutput}/${name}.png`; await target.screenshot({ path: `${output}${name}.png` }); report.captures.push({ name, path, canvas: pixels });
}
async function teleport(target, landmark, purpose) {
  await release(target); await target.evaluate(name => window.__ATHEN__.goto(name), landmark); await target.waitForTimeout(180);
  report.teleports.push({ landmark, purpose, player: (await snapshot(target)).player });
}
async function orient(target, yaw) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const current = await target.evaluate(() => window.__ATHEN__.camera.yaw), difference = wrappedAngle(yaw - current);
    if (Math.abs(difference) < .015) return;
    const width = target.viewportSize().width, dx = Math.max(-width * .55, Math.min(width * .55, difference / -.003));
    const x = width / 2 - dx / 2, y = target.viewportSize().height * .48;
    await target.mouse.move(x, y); await target.mouse.down({ button: 'right' }); await target.mouse.move(x + dx, y, { steps: 3 }); await target.mouse.up({ button: 'right' });
  }
  assert(Math.abs(wrappedAngle(yaw - await target.evaluate(() => window.__ATHEN__.camera.yaw))) < .02, 'RMB orients fixture approach.');
}
async function openNPC(target, id, landmark, touch = false) {
  await teleport(target, landmark, `Interaction fixture for ${id}`);
  const state = await snapshot(target), actor = state.npcs.actors.find(actor => actor.id === id);
  if (Math.hypot(actor.position[0] - state.player.x, actor.position[2] - state.player.z) > .8) {
    await orient(target, Math.atan2(state.player.x - actor.position[0], state.player.z - actor.position[2]));
    await target.keyboard.down('w'); await target.waitForTimeout(190); await target.keyboard.up('w'); await target.waitForTimeout(160);
  }
  await target.waitForFunction(npc => window.__ATHEN__.npcs.nearest?.id === npc, id, { timeout: 4000 });
  await target.locator('canvas').focus();
  if (touch) await target.locator('#touch-interact').tap(); else await target.keyboard.press('e');
  await target.waitForFunction(() => window.__ATHEN__.state === 'dialogue');
  const opened = await snapshot(target); assert.equal(opened.dialogue.speaker, actor.name); assert.equal(opened.dialogue.choices.length, 2);
  assert.equal(await target.locator('#dialogue-choices button').count(), 2); return opened;
}
async function escape(target = page) {
  await target.keyboard.press('Escape'); await target.waitForFunction(() => window.__ATHEN__.state === 'play');
  assert(await target.evaluate(() => document.activeElement === document.querySelector('canvas')), 'Closing overlay restores canvas focus.');
}
async function focusInside(target, selector) {
  assert(await target.locator(selector).evaluate(panel => panel.contains(document.activeElement) && !document.activeElement.disabled), `Focus remains on an enabled control inside ${selector}.`);
}
async function fit(target, label) {
  const value = await target.evaluate(() => ({ viewport: [innerWidth, innerHeight], scrollWidth: document.documentElement.scrollWidth,
    panels: [...document.querySelectorAll('.game-panel')].filter(panel => !panel.hidden).map(panel => { const r = panel.getBoundingClientRect();
      return { id: panel.id, bounds: [r.left, r.top, r.right, r.bottom], fits: r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 }; }) }));
  report.layoutChecks.push({ label, ...value });
  const fits = value.scrollWidth <= value.viewport[0] + 1 && value.panels.every(panel => panel.fits);
  if (!fits) await capture(target, `${label.replace(/\W+/g, '-')}-overflow`);
  assert(fits, `${label} fits viewport.`); return value;
}

try {
  const baseline = JSON.parse(await readFile(baselinePath, 'utf8')); assert.equal(baseline.result, 'PASS'); assert(baseline.mainRoute.completed && baseline.mainRoute.teleportCount === 0);
  browser = await chromium.launch({ headless: false, args: process.platform === 'darwin' ? ['--use-angle=metal'] : [] });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page = await context.newPage(); await observe(page, 'desktop'); await page.bringToFront(); report.identity = await boot(page);
  const physical = await page.evaluate(() => ({ colliders: window.__ATHEN__.colliders, physics: window.__ATHEN__.physics }));
  const colliders = list => canonical([...list].sort((a, b) => a.name.localeCompare(b.name)));
  const keys = ['engine', 'timestep', 'bodies', 'colliders', 'staticColliders', 'characterControllers', 'ccdBodies', 'sensors', 'collisionGroups', 'character', 'cameraCastRadius'];
  const config = value => canonical(Object.fromEntries(keys.map(key => [key, value[key]])));
  report.routeEquivalence = { baseline: baselinePath, priorRoute: baseline.mainRoute, colliderCount: physical.colliders.length,
    identicalColliders: colliders(physical.colliders) === colliders(baseline.initial.colliders), identicalController: config(physical.physics) === config(baseline.initial.physics),
    colliderHash: createHash('sha256').update(colliders(physical.colliders)).digest('hex') };
  assert(report.routeEquivalence.identicalColliders && report.routeEquivalence.identicalController, 'Repeat continuous route if the physical configuration changed.');
  report.checks.push('Normal production UI and Phase5 debug data available; prior no-teleport route retained by exact physical equivalence.');

  report.conversations = [];
  for (const [id, landmark] of [['npc_vex', 'west_gate'], ['npc_torr', 'mission_slab'], ['npc_linn', 'oa_hill']]) {
    const opened = await openNPC(page, id, landmark); await focusInside(page, '#dialogue-panel');
    const before = opened.player; await page.keyboard.down('w'); await page.waitForTimeout(200); const blocked = await snapshot();
    assert(horizontalDistance(before, blocked.player) < .001 && Math.abs(before.y - blocked.player.y) < .001, 'Dialogue freezes the capsule.'); await release();
    for (let i = 0; i < 6; i++) { await page.keyboard.press('Tab'); await focusInside(page, '#dialogue-panel'); }
    await page.keyboard.press('Shift+Tab'); await focusInside(page, '#dialogue-panel');
    const lore = opened.dialogue.choices.find(choice => choice.next); assert(lore);
    await page.locator(`[data-choice="${lore.id}"]`).click(); const followup = await snapshot();
    assert.equal(followup.dialogue.choices.length, 2); assert.notEqual(followup.dialogue.text, opened.dialogue.text);
    await capture(page, `${id}-dialogue`); await escape();
    await page.keyboard.press('e'); await page.waitForFunction(() => window.__ATHEN__.state === 'dialogue');
    await page.locator('[data-choice="leave"]').focus(); await page.keyboard.press('Enter'); await page.waitForFunction(() => window.__ATHEN__.state === 'play');
    report.conversations.push({ id, speaker: opened.dialogue.speaker, greeting: opened.dialogue, followup: followup.dialogue });
  }
  const mira = await openNPC(page, 'npc_mira', 'basic_general'); report.conversations.push({ id: 'npc_mira', greeting: mira.dialogue });
  await page.locator('[data-choice="browse"]').focus(); await page.keyboard.press('Enter'); await page.waitForFunction(() => window.__ATHEN__.state === 'shop');
  await focusInside(page, '#shop-panel'); assert.equal((await snapshot()).inventory.credits, 25);
  async function trade(operation, id) {
    const before = (await snapshot()).inventory; const button = page.locator(`[data-${operation}="${id}"]`); await button.focus(); await page.keyboard.press('Enter');
    await page.waitForFunction(([op, previous]) => window.__ATHEN__.inventory[op === 'buy' ? 'purchases' : 'sales'] === previous + 1,
      [operation, before[operation === 'buy' ? 'purchases' : 'sales']]);
    const after = (await snapshot()).inventory, item = before.items.find(item => item.id === id);
    assert.equal(quantity(after, id) - quantity(before, id), operation === 'buy' ? 1 : -1);
    assert.equal(after.credits - before.credits, operation === 'buy' ? -item.buyPrice : item.sellPrice);
    await focusInside(page, '#shop-panel'); return after;
  }
  await trade('buy', 'water_flask'); await trade('sell', 'scrap_coil');
  assert(await page.locator('[data-sell="scrap_coil"]').isDisabled());
  await trade('buy', 'scrap_coil'); let traded = await trade('sell', 'scrap_coil');
  assert.equal(traded.credits, 21); assert.equal(quantity(traded, 'water_flask'), 1);
  while (traded.credits >= 9) traded = await trade('buy', 'medkit');
  assert(await page.locator('[data-buy="medkit"]').isDisabled()); assert(await page.locator('[data-buy="water_flask"]').isDisabled());
  const disabled = await page.locator('[data-buy="medkit"]').boundingBox();
  await page.mouse.click(disabled.x + disabled.width / 2, disabled.y + disabled.height / 2); assert.deepEqual((await snapshot()).inventory, traded);
  report.inventory = traded; await capture(page, 'shop-desktop'); await escape();
  report.checks.push('All four NPCs open through real E with two choices; lore, close, focus trapping and blocked movement work; Mira trades are one unit each, with empty/poor-wallet controls disabled.');

  await teleport(page, 'west_gate', 'Quick-slot keyboard fixtures'); await page.locator('canvas').focus();
  for (let index = 0; index < 6; index++) {
    await page.keyboard.press(String(index + 1));
    assert.equal(await page.locator(`[data-hotbar="${index}"]`).getAttribute('aria-pressed'), 'true');
    if (index === 3) { await page.waitForFunction(() => window.__ATHEN__.state === 'dialogue'); await escape(); }
    if (index >= 4) {
      const selector = index === 4 ? '#inventory' : '#city-notes'; assert(await page.locator(selector).evaluate(node => node.open), `Keyboard slot ${index + 1} opens its details.`);
      await page.keyboard.press(String(index + 1)); assert.equal(await page.locator(selector).evaluate(node => node.open), false);
    }
  }
  await page.keyboard.press('Escape'); await page.waitForFunction(() => window.__ATHEN__.state === 'paused');
  const paused = await snapshot(); await page.waitForTimeout(200); const held = await snapshot();
  assert.deepEqual(held.player, paused.player); assert.deepEqual(held.playerAnimation, paused.playerAnimation); assert.deepEqual(held.npcs, paused.npcs);
  await page.keyboard.press('e'); assert.equal((await snapshot()).state, 'paused'); await escape();
  report.checks.push('Keyboard slots1–6 dispatch their intended actions; Escape pauses bones/physics exactly and resumes with canvas focus.');

  await teleport(page, 'grid_kiosk', 'Lattice interaction fixture'); assert.equal((await snapshot()).interaction.kind, 'lattice');
  const latticeStart = Date.now(), beforeGrid = (await snapshot()).player; await page.keyboard.press('e'); await page.waitForFunction(() => window.__ATHEN__.state === 'grid');
  assert.equal((await snapshot()).grid.phase, 'tunnel'); await capture(page, 'lattice-tunnel');
  await page.waitForFunction(() => window.__ATHEN__.grid?.phase === 'map', null, { timeout: 5000 });
  const grid = (await snapshot()).grid; assert.equal(grid.nodes.length, 3); assert(Date.now() - latticeStart >= 1150, 'Connection retains its1.25second transition.');
  assert(horizontalDistance(beforeGrid, (await snapshot()).player) < .001);
  for (const node of grid.nodes) {
    await page.locator(`[data-node="${node.id}"]`).click();
    await page.waitForFunction(id => window.__ATHEN__.grid?.selectedNode === id, node.id);
    assert((await snapshot()).logs.some(log => log.text.includes(`Link established to ${node.name}`)));
  }
  await capture(page, 'lattice-map'); report.grid = (await snapshot()).grid; await escape();
  await teleport(page, 'whompah', 'Optional Ring Gate interaction fixture');
  await page.keyboard.press('e'); assert((await snapshot()).logs.some(log => /Destination offline/.test(log.text)));
  const completed = await snapshot(); assert.equal(completed.story.spokenCount, 4); assert.equal(completed.story.complete, true);
  report.story = completed.story; await capture(page, 'visit-complete');
  report.checks.push('Lattice transition reaches three selectable original nodes without moving the capsule; Ring Gate barks offline; the complete visit objective is true.');

  await teleport(page, 'west_gate', '1080p moving performance fixture'); await orient(page, -Math.PI / 2); await page.locator('canvas').focus(); await page.keyboard.down('w');
  try { report.performance = await page.evaluate(async () => {
    const times = [], samples = []; await new Promise(resolve => { const frame = time => { times.push(time); samples.push(window.__ATHEN__.renderer);
      if (times.length < 121) requestAnimationFrame(frame); else resolve(); }; requestAnimationFrame(frame); });
    const gl = document.querySelector('canvas').getContext('webgl2'), ext = gl.getExtension('WEBGL_debug_renderer_info');
    return { fps: 120000 / (times.at(-1) - times[0]), maxDraws: Math.max(...samples.map(s => s.draws)), maxTris: Math.max(...samples.map(s => s.tris)),
      gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unavailable', renderer: window.__ATHEN__.renderer,
      instances: window.__ATHEN__.characters.instances, viewport: [innerWidth, innerHeight], userAgent: navigator.userAgent };
  }); } finally { await release(); }
  assert(report.performance.fps >= 58 && report.performance.maxDraws <= 80 && report.performance.maxTris <= 250000, JSON.stringify(report.performance));
  assert.deepEqual(report.performance.viewport, [1920, 1080]); assert.equal(report.performance.instances, 8);
  assert(!/SwiftShader|software/i.test(report.performance.gpu), 'Native GPU required.'); if (process.platform === 'darwin') assert(/Metal/i.test(report.performance.gpu));
  report.checks.push('1920×1080 movement holds >=58fps on the reported native GPU within80draw/250ktriangle budgets.');

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const mobile = await mobileContext.newPage(); await observe(mobile, 'mobile'); await mobile.bringToFront(); await boot(mobile);
  report.mobile = { play: await fit(mobile, 'mobile play') }; await capture(mobile, 'mobile-play');
  report.mobile.quickMenus = [];
  for (const [slot, selector] of [[4, '#inventory .inventory-content'], [5, '#city-notes>div']]) {
    await mobile.locator(`[data-hotbar="${slot}"]`).tap();
    const panel = mobile.locator(selector); assert(await panel.isVisible(), `Mobile quick slot ${slot + 1} opens visible content.`);
    const bounds = await panel.boundingBox();
    assert(bounds && bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= 391 && bounds.y + bounds.height <= 845);
    report.mobile.quickMenus.push({ slot: slot + 1, bounds }); await capture(mobile, `mobile-slot-${slot + 1}`);
    await mobile.locator(`[data-hotbar="${slot}"]`).tap(); assert.equal(await panel.isVisible(), false);
  }
  await openNPC(mobile, 'npc_mira', 'basic_general', true); report.mobile.dialogue = await fit(mobile, 'mobile dialogue'); await capture(mobile, 'mobile-dialogue');
  await mobile.locator('[data-choice="browse"]').tap(); await mobile.waitForFunction(() => window.__ATHEN__.state === 'shop');
  report.mobile.shop = await fit(mobile, 'mobile shop'); await mobile.locator('[data-buy="water_flask"]').tap();
  assert.equal(quantity((await snapshot(mobile)).inventory, 'water_flask'), 1); await capture(mobile, 'mobile-shop');
  await mobile.locator('#shop-panel [data-close]').tap(); await mobile.waitForFunction(() => window.__ATHEN__.state === 'play');
  await teleport(mobile, 'grid_kiosk', 'Mobile Lattice fixture'); await mobile.locator('#touch-interact').tap();
  await mobile.waitForFunction(() => window.__ATHEN__.grid?.phase === 'map'); report.mobile.grid = await fit(mobile, 'mobile grid');
  await mobile.locator('[data-node]').first().tap(); assert((await snapshot(mobile)).grid.selectedNode); await capture(mobile, 'mobile-grid');
  report.checks.push('390×844 production HUD/dialogue/shop/grid fit; actual touch opens Mira, buys one flask and selects a Lattice node.');
  await Promise.all(jobs); assert.deepEqual(report.errors, []); report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
  if (page) try { await release(); report.failureState = await snapshot(); await page.screenshot({ path: `${output}failure.png` }); } catch {}
} finally {
  await Promise.allSettled(jobs); await browser?.close(); report.elapsedMs = Date.now() - started;
  await writeFile(`${output}report.json`, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ result: report.result, output: report.output, checks: report.checks, teleportCount: report.teleports.length,
    performance: report.performance, story: report.story, errors: report.errors, failure: report.failure, limitations: report.limitations }, null, 2));
}

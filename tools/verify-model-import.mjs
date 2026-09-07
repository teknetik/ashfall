import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { chromium } from '@playwright/test';

const url = process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:4174';
const output = `tools/model-import/${new Date().toISOString().replaceAll(':', '-')}`;
await mkdir(output, { recursive: true });
const report = { url, output, errors: [], cameras: [], interactions: [], limitations: [
  'The supplied guard GLB contains a static pose. Runtime state aliases do not constitute authored idle/talk/walk/run motion.',
  'Performance applies to this workstation and browser, not an untested laptop.',
] };
const browser = await chromium.launch({ channel: 'chrome', headless: false, args: ['--no-sandbox', '--use-angle=gl'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', error => report.errors.push(error.message));
page.on('requestfailed', req => report.errors.push(`${req.url()}: ${req.failure()?.errorText}`));
const snap = () => page.evaluate(() => ({ state: __ATHEN__.state, error: __ATHEN__.error,
  npcs: __ATHEN__.npcs, player: __ATHEN__.player, characters: __ATHEN__.characters,
  playerAnimation: __ATHEN__.playerAnimation, renderer: __ATHEN__.renderer, dialogue: __ATHEN__.dialogue }));
try {
  await page.goto(url);
  await page.waitForFunction(() => window.__ATHEN__ && __ATHEN__.state !== 'boot', null, { timeout: 60000 });
  await page.evaluate(() => __ATHEN__.ready);
  await page.bringToFront();
  await page.waitForTimeout(3000);
  report.initial = await snap();
  assert.equal(report.initial.state, 'play', report.initial.error);
  assert.equal(report.initial.npcs.actors.length, 7);
  const guard = report.initial.characters.assets.guard;
  assert(guard.triangles <= 6000 && guard.bones === 24 && guard.materials.length === 1);
  assert(guard.textures.some(t => t.width === 2048 && t.height === 2048));
  assert(Math.abs(guard.bounds.max[1] - guard.bounds.min[1] - 1.8) < .03);
  for (const actor of report.initial.npcs.actors) {
    assert.equal(actor.character.variant, actor.role === 'ambient' ? 'default' : 'guard');
    assert(actor.character.source.endsWith(actor.role === 'ambient' ? '/npcs.glb' : '/ward-guard.glb'));
    assert.equal(actor.character.staticPose, actor.role !== 'ambient');
    assert(actor.character.pose.length >= 4, 'Actual rig bone diagnostics must exist.');
  }
  const fetched = Buffer.from(await (await fetch(`${url}/assets/ward-guard.glb`)).arrayBuffer());
  const disk = await readFile('public/assets/ward-guard.glb');
  assert(fetched.equals(disk), 'Production preview must serve the new guard bytes.');
  report.guardSha256 = createHash('sha256').update(disk).digest('hex');
  await page.screenshot({ path: `${output}/guard-at-gate.png` });
  for (const camera of ['cam_gate', 'cam_avenue', 'cam_hill', 'cam_grid', 'cam_whompah', 'cam_hero']) {
    await page.evaluate(name => __ATHEN__.view(name), camera);
    await page.waitForTimeout(2200);
    const renderer = await page.evaluate(() => __ATHEN__.renderer);
    assert(renderer.draws <= 80 && renderer.tris <= 250000, JSON.stringify({ camera, renderer }));
    assert(renderer.fps >= 58, `${camera}: ${renderer.fps} fps`);
    report.cameras.push({ camera, ...renderer });
    await page.evaluate(name => __ATHEN__.shot(name), camera);
    await page.screenshot({ path: `${output}/${camera}.png` });
  }
  await page.evaluate(() => __ATHEN__.view('follow'));
  for (const [id, landmark] of [['npc_vex', 'west_gate'], ['npc_torr', 'mission_slab'], ['npc_linn', 'oa_hill'], ['npc_mira', 'basic_general']]) {
    await page.evaluate(name => __ATHEN__.goto(name), landmark);
    await page.waitForTimeout(250);
    const s = await snap(), actor = s.npcs.actors.find(a => a.id === id);
    if (Math.hypot(s.player.x - actor.position[0], s.player.z - actor.position[2]) > .8) {
      const yaw = Math.atan2(s.player.x - actor.position[0], s.player.z - actor.position[2]);
      for (let i = 0; i < 6; i++) {
        const current = await page.evaluate(() => __ATHEN__.camera.yaw);
        const difference = Math.atan2(Math.sin(yaw - current), Math.cos(yaw - current));
        if (Math.abs(difference) < .015) break;
        const dx = Math.max(-1000, Math.min(1000, difference / -.003));
        await page.mouse.move(960 - dx / 2, 500); await page.mouse.down({ button: 'right' });
        await page.mouse.move(960 + dx / 2, 500, { steps: 3 }); await page.mouse.up({ button: 'right' });
      }
      await page.keyboard.down('w'); await page.waitForTimeout(190); await page.keyboard.up('w');
    }
    await page.waitForFunction(npc => __ATHEN__.npcs.nearest?.id === npc, id);
    await page.locator('canvas').focus(); await page.keyboard.press('e');
    await page.waitForFunction(() => __ATHEN__.state === 'dialogue');
    const dialog = await page.evaluate(() => __ATHEN__.dialogue);
    assert.equal(dialog.speaker, actor.name); assert.equal(dialog.choices.length, 2);
    report.interactions.push({ id, speaker: dialog.speaker });
    await page.screenshot({ path: `${output}/${id}-dialogue.png` });
    await page.keyboard.press('Escape'); await page.waitForFunction(() => __ATHEN__.state === 'play');
  }
  const after = await snap();
  for (const before of report.initial.npcs.actors.filter(a => a.role === 'ambient')) {
    const walker = after.npcs.actors.find(a => a.id === before.id);
    assert.notDeepEqual(walker.position, before.position, 'Ambient walker must still move.');
    assert.equal(walker.character.animation, 'walk');
  }
  await page.keyboard.down('w'); await page.waitForTimeout(600);
  assert.equal((await snap()).playerAnimation.animation, 'walk');
  await page.keyboard.down('Shift'); await page.waitForTimeout(500);
  assert.equal((await snap()).playerAnimation.animation, 'run');
  await page.keyboard.up('Shift'); await page.keyboard.up('w');
  assert.equal(report.errors.length, 0, report.errors.join('\n'));
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
  await page.screenshot({ path: `${output}/failure.png` });
} finally {
  await writeFile(`${output}/report.json`, JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ result: report.result, output, cameras: report.cameras, interactions: report.interactions,
    errors: report.errors, failure: report.failure }, null, 2));
}

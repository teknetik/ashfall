import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import { Vector3, Quaternion } from 'three';
import { chromium } from '@playwright/test';

const require = createRequire(import.meta.url);
const sourcePath = fileURLToPath(new URL('../../src/npc.ts', import.meta.url));
const baselinePath = process.env.ATHEN_NPC_COLLIDERS
  ?? fileURLToPath(new URL('../phase3-support/runs/2026-09-07T10-05-42.477Z-16797/report.json', import.meta.url));
const devURL = process.env.ATHEN_QA_URL ?? 'http://127.0.0.1:5173';
const output = fileURLToPath(new URL(`./npc-fixtures/${new Date().toISOString().replaceAll(':', '-')}-${process.pid}.json`, import.meta.url));
await mkdir(fileURLToPath(new URL('./npc-fixtures/', import.meta.url)), { recursive: true });
const report = { result: 'RUNNING', sourcePath, baselinePath, devURL,
  scope: 'NPC placement against recorded world colliders and isolated browser entity/DOM logic. The injected actor fixtures do not establish authored-rig visual acceptance.' };
let browser;
try {
  // Evaluate the actual definitions without instantiating characters or a DOM.
  const compiled = ts.transpileModule(await readFile(sourcePath, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const moduleExports = {};
  new Function('require', 'exports', compiled)(require, moduleExports);
  const colliders = JSON.parse(await readFile(baselinePath, 'utf8')).initial.colliders;
  const samples = moduleExports.NPC_DEFINITIONS.map(npc => ({ id: npc.id, position: npc.position }));
  for (const walker of moduleExports.AMBIENT_WALKERS) {
    for (let index = 0; index < walker.waypoints.length; index++) {
      const a = walker.waypoints[index], b = walker.waypoints[(index + 1) % walker.waypoints.length];
      const steps = Math.ceil(Math.hypot(b[0] - a[0], b[2] - a[2]) / .15);
      for (let step = 0; step <= steps; step++) {
        const t = step / steps;
        samples.push({ id: walker.id, position: [a[0] + (b[0] - a[0]) * t, a[1], a[2] + (b[2] - a[2]) * t] });
      }
    }
  }
  const overlaps = [], unsupported = [];
  for (const { id, position: p } of samples) {
    let supported = p[1] === 0;
    for (const c of colliders) {
      if (c.kind === 'halfspace') continue;
      if (c.kind === 'box' && Math.hypot(...(c.rotation ?? [0, 0, 0, 1]).slice(0, 3)) < 1e-6
        && Math.abs(p[0] - c.position[0]) < c.halfExtents[0] && Math.abs(p[2] - c.position[2]) < c.halfExtents[2]
        && Math.abs(p[1] - c.position[1] - c.halfExtents[1]) < 1e-5) supported = true;
      if (Math.hypot(p[0] - c.position[0], p[2] - c.position[2]) > Math.hypot(...(c.halfExtents ?? [c.radius, c.halfHeight, c.radius])) + 2) continue;
      // Sample a conservative upright 1.8 m body; inverse rotation handles OBBs.
      for (let height = .32; height <= 1.48; height += .08) {
        let distance;
        if (c.kind === 'box') {
          const q = new Quaternion(...(c.rotation ?? [0, 0, 0, 1])).invert();
          const v = new Vector3(p[0] - c.position[0], p[1] + height - c.position[1], p[2] - c.position[2]).applyQuaternion(q);
          distance = Math.hypot(...[v.x, v.y, v.z].map((value, index) => Math.max(Math.abs(value) - c.halfExtents[index], 0)));
        } else distance = Math.hypot(Math.max(Math.hypot(p[0] - c.position[0], p[2] - c.position[2]) - c.radius, 0),
          Math.max(Math.abs(p[1] + height - c.position[1]) - c.halfHeight, 0));
        if (distance < .31) { overlaps.push({ id, position: p, collider: c.name }); break; }
      }
    }
    if (!supported) unsupported.push({ id, position: p });
  }
  report.placement = { samples: samples.length, radius: .32, height: 1.8, overlaps, unsupported };
  assert.equal(overlaps.length, 0); assert.equal(unsupported.length, 0);

  browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  await page.route('**/__npc-logic-test', route => route.fulfill({ contentType: 'text/html', body:
    '<!doctype html><div id="a" style="position:relative;width:800px;height:600px"><canvas width="800" height="600" style="width:800px;height:600px"></canvas></div><div id="b"></div>' }));
  await page.goto(new URL('/__npc-logic-test', devURL).href);
  report.logic = await page.evaluate(async () => {
    const { NPCSystem } = await import('/src/npc.ts');
    const { Group, Scene, PerspectiveCamera } = await import('/node_modules/three/build/three.module.js');
    const records = [];
    const library = () => {
      const ids = new Set();
      return { create({ id }) {
        if (ids.has(id)) throw new Error(`Duplicate fixture id: ${id}`);
        ids.add(id);
        const record = { id, root: new Group(), motion: null, disposed: 0, diagnostics: { source: 'isolated actor fixture' } };
        record.update = (_dt, motion) => { record.motion = motion; };
        record.dispose = () => { record.disposed++; ids.delete(id); };
        records.push(record); return record;
      } };
    };
    const a = new NPCSystem(new Scene(), library(), document.querySelector('#a'));
    const b = new NPCSystem(new Scene(), library(), document.querySelector('#b'));
    const pose = { position: { x: -8, y: .5, z: 17.8 }, yaw: 0 };
    a.update(10, pose); for (let i = 0; i < 100; i++) b.update(.1, pose);
    const aa = a.diagnostics.actors.filter(actor => actor.role === 'ambient'), bb = b.diagnostics.actors.filter(actor => actor.role === 'ambient');
    const maxPositionDifference = Math.max(...aa.flatMap((actor, index) => actor.position.map((value, axis) => Math.abs(value - bb[index].position[axis]))));
    const nearest = a.nearest; let hook = null; a.onInteract = target => { hook = target.id; };
    const interaction = a.interact(); a.update(.1, pose);
    const talking = records.find(actor => actor.id === 'npc_mira').motion.talking;
    const camera = new PerspectiveCamera(50, 800 / 600, .1, 200);
    camera.position.set(-8, 2.8, 23); camera.lookAt(-8, 1.5, 15.8);
    a.projectLabels(camera, document.querySelector('canvas'));
    const label = document.querySelector('#a [data-npc="npc_mira"]'), rect = label.getBoundingClientRect();
    const labelVisible = !label.hidden;
    camera.lookAt(-8, 1.5, 35); a.projectLabels(camera, document.querySelector('canvas'));
    const behindHidden = label.hidden;
    a.update(0, { ...pose, yaw: Math.PI }); const behindTarget = a.nearest;
    a.update(0, { position: { x: -8, y: .5, z: 20 }, yaw: 0 }); const distantTarget = a.nearest;
    const beforeDispose = a.diagnostics;
    a.dispose(); b.dispose(); a.dispose();
    return { instances: beforeDispose.instanceCount, named: beforeDispose.namedCount, ambient: beforeDispose.ambientCount,
      maxPositionDifference, nearest, hook, interaction: interaction?.id, talking, labelVisible,
      labelBounds: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }, behindHidden, behindTarget, distantTarget,
      disposalCounts: records.map(actor => actor.disposed), remainingLabelLayers: document.querySelectorAll('.npc-label-layer').length };
  });
  const result = report.logic;
  assert.equal(result.instances, 7); assert.equal(result.named, 4); assert.equal(result.ambient, 3);
  assert(result.maxPositionDifference < 1e-8); assert.equal(result.nearest.id, 'npc_mira'); assert.equal(result.hook, 'npc_mira');
  assert(result.talking && result.labelVisible && result.behindHidden); assert.equal(result.behindTarget, null); assert.equal(result.distantTarget, null);
  assert(result.disposalCounts.every(count => count === 1)); assert.equal(result.remainingLabelLayers, 0);
  report.result = 'PASS';
} catch (error) {
  report.result = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
} finally {
  await browser?.close();
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ ...report, output }, null, 2));
}

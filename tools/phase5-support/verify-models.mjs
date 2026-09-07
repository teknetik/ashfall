// Pure model regressions. Compile the exact TypeScript source in memory.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import ts from 'typescript';
async function sourceModule(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
}
const { Shop, ITEMS } = await sourceModule('../../src/shop.ts');
const { getDialogue } = await sourceModule('../../src/dialogue.ts');
const checks = [];
const quantity = (snapshot, id) => snapshot.items.find(item => item.id === id).quantity;
{
  const shop = new Shop();
  assert.equal(shop.snapshot.credits, 25);
  assert.deepEqual(shop.snapshot.items.map(item => [item.id, item.quantity]), [['water_flask', 0], ['medkit', 0], ['scrap_coil', 1]]);
  assert.deepEqual(Object.values(ITEMS).map(item => [item.id, item.buyPrice, item.sellPrice]), [['water_flask', 4, 2], ['medkit', 9, 4], ['scrap_coil', 2, 1]]);
  assert.equal(shop.sell('scrap_coil').ok, true);
  assert.equal(shop.buy('scrap_coil').ok, true);
  assert.equal(shop.sell('scrap_coil').ok, true);
  assert.equal(shop.buy('water_flask').ok, true);
  assert.equal(shop.snapshot.credits, 21);
  assert.equal(quantity(shop.snapshot, 'water_flask'), 1);
  assert.equal(quantity(shop.snapshot, 'scrap_coil'), 0);
  assert.equal(shop.snapshot.purchases, 2);
  assert.equal(shop.snapshot.sales, 2);
  checks.push('Start with 25 credits and one scrap coil; selling/buying/selling scrap and buying a flask transfers one unit each with the expected balances.');
}
{
  const shop = new Shop();
  shop.buy('medkit'); shop.buy('medkit');
  const before = shop.snapshot;
  assert.equal(shop.buy('medkit').ok, false);
  assert.deepEqual(shop.snapshot, before);
  assert.equal(shop.sell('water_flask').ok, false);
  assert.deepEqual(shop.snapshot, before);
  shop.sell('scrap_coil'); const sold = shop.snapshot;
  assert.equal(shop.sell('scrap_coil').ok, false); assert.deepEqual(shop.snapshot, sold);
  checks.push('Insufficient funds and overselling leave credits, inventory and success counters unchanged.');
}
{
  const shop = new Shop();
  shop.buy('medkit'); shop.buy('medkit'); shop.sell('scrap_coil');
  assert.equal(shop.snapshot.credits, 8);
  assert.equal(shop.buy('water_flask').ok, true);
  assert.equal(shop.buy('water_flask').ok, true);
  assert.equal(shop.snapshot.credits, 0);
  assert.equal(quantity(shop.snapshot, 'water_flask'), 2);
  const emptyWallet = shop.snapshot;
  assert.equal(shop.buy('scrap_coil').ok, false); assert.deepEqual(shop.snapshot, emptyWallet);
  checks.push('An exact-price purchase can spend the wallet down to zero; a subsequent purchase fails atomically.');
}
{
  const shop = new Shop(), before = shop.snapshot;
  for (const invalid of ['', '__proto__', 'constructor', 'toString', 'MEDKIT', null, undefined, 0, NaN, Infinity, {}, Object.create(null)]) {
    for (const action of ['buy', 'sell']) {
      const result = shop[action](invalid);
      assert.equal(result.ok, false); assert.equal(result.itemId, null); assert.deepEqual(shop.snapshot, before);
    }
  }
  assert.equal(Reflect.set(before, 'credits', Infinity), false);
  assert.equal(Reflect.set(before.items[0], 'quantity', -100), false);
  assert.equal(Reflect.set(ITEMS.water_flask, 'buyPrice', -4), false);
  assert.equal(Reflect.set(ITEMS, 'free_item', { buyPrice: 0 }), false);
  shop.buy('water_flask'); assert.equal(quantity(before, 'water_flask'), 0);
  assert.equal(new Shop().snapshot.credits, 25);
  checks.push('Unknown, prototype and non-finite IDs fail safely; snapshots/catalogue are immutable and sessions are independent.');
}
{
  // Repeated varied actions verify conservation and atomicity without duplicating the transaction implementation.
  let seed = 1741, attempts = 0, successfulBuys = 0, successfulSales = 0;
  const shop = new Shop(), ids = Object.keys(ITEMS);
  for (let i = 0; i < 1000; i++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const id = ids[seed % ids.length], action = (seed & 4) ? 'buy' : 'sell';
    const before = shop.snapshot, result = shop[action](id), after = shop.snapshot; attempts++;
    if (!result.ok) assert.deepEqual(after, before);
    else {
      assert.equal(result.itemId, id);
      const unitDelta = action === 'buy' ? 1 : -1;
      assert.equal(quantity(after, id) - quantity(before, id), unitDelta);
      assert.equal(after.credits - before.credits, action === 'buy' ? -ITEMS[id].buyPrice : ITEMS[id].sellPrice);
      for (const other of ids.filter(other => other !== id)) assert.equal(quantity(after, other), quantity(before, other));
      if (action === 'buy') successfulBuys++; else successfulSales++;
    }
    for (const amount of [after.credits, after.purchases, after.sales, ...after.items.map(item => item.quantity)]) assert.ok(Number.isSafeInteger(amount) && amount >= 0);
    assert.equal(after.purchases, successfulBuys); assert.equal(after.sales, successfulSales);
  }
  assert.equal(attempts, 1000); assert.ok(successfulBuys > 0 && successfulSales > 0);
  checks.push('1,000 deterministic varied trades preserve whole nonnegative balances, single-unit transfers, unrelated items and success-only counters.');
}
{
  const speakers = { npc_mira: 'Mira', npc_torr: 'Torr', npc_vex: 'Vex', npc_linn: 'Linn' };
  let nodeCount = 0, shopChoices = 0;
  for (const [npc, speaker] of Object.entries(speakers)) {
    const pending = ['greeting'], seen = new Set();
    while (pending.length) {
      const id = pending.shift(); if (seen.has(id)) continue; seen.add(id);
      const node = getDialogue(npc, id); nodeCount++;
      assert.equal(node.speaker, speaker); assert.ok(node.title && node.text); assert.equal(node.choices.length, 2);
      assert.equal(new Set(node.choices.map(choice => choice.id)).size, 2);
      assert.equal(Reflect.set(node.choices[0], 'label', 'mutated'), false);
      assert.ok(node.choices.some(choice => choice.action === 'close'));
      for (const choice of node.choices) {
        assert.ok(choice.id && choice.label); assert.notEqual(Boolean(choice.next), Boolean(choice.action));
        if (choice.next) { getDialogue(npc, choice.next); pending.push(choice.next); }
        else assert.ok(['shop', 'close'].includes(choice.action));
        if (choice.action === 'shop') { shopChoices++; assert.equal(npc, 'npc_mira'); }
      }
    }
    assert.equal(seen.size, npc === 'npc_mira' ? 1 : 2);
    assert.throws(() => getDialogue(npc, 'missing'), /Unknown dialogue node/);
  }
  assert.equal(nodeCount, 7); assert.equal(shopChoices, 1);
  for (const id of ['missing', '__proto__', 'constructor']) assert.throws(() => getDialogue(id), /Unknown dialogue NPC/);
  checks.push('All seven original dialogue nodes have exactly two unique choices, valid links, a close action and correct speakers; only Mira opens the shop.');
}
const report = { result: 'PASS', checks, transactionAttempts: 1000, dialogueNodes: 7, note: 'Pure source-model checks only; browser interactions and UI accessibility are separate acceptance checks.' };
await writeFile(new URL('./model-checks.json', import.meta.url), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));

#!/usr/bin/env python3
"""Order 2 ("Keep the Charge") grind simulation for the Ward loot tables (30 Sep 2026).

Replicates LootBook exactly (SplitMix64, declared-order rolls, per table+item miss counters, pityAfter) and reads
loot tables from WardCrafting.asset: the committed baseline (git HEAD by default) and the working tree.

Player model: primer = first-contact drone, then the depot nest (drone + 2 workers, kill order shuffled by the seed);
order 1 (grip) needs no extra rolls. Order 2 needs 2 capacitors and 2 copper filament (the primer's 2 scrap coils cover
the "any conductor" line). depot-first: clear the depot nest once, search every ready heap on the depot route
(6 scrap heaps, 2 carcasses, 1 crashed drone), clear the depot again, ... until both needs are met. heaps-first: the
heaps (the nest was just cleared) before the next clear. Result pairs are (depot clears, heap searches) after the primer.

  python3 loot_sim.py [--baseline REV] [--seeds N] [--strategy heaps-first] [--lose-depot-drone-caches]
"""
import argparse, random, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSET = 'unity/AthenHill/Assets/AthenHill/Data/Crafting/WardCrafting.asset'
REPO = HERE.parents[3]
M = (1 << 64) - 1


class Rng:
    def __init__(self, seed): self.s = seed & M
    def next(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & M
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M
        return z ^ (z >> 31)
    def double(self): return (self.next() >> 11) * (1.0 / (1 << 53))
    def int(self, n): return 0 if n <= 1 else self.next() % n


def tables(text):
    out = {}
    block = text[text.index('lootTables:'):text.index('slotLabels:')]
    for t in re.split(r'\n  - id: ', block)[1:]:
        tid = t.split('\n')[0].strip()
        entries = []
        for e in re.split(r'\n    - itemId: ', t)[1:]:
            f = dict(re.findall(r'(\w+): ([\w.]+)', 'itemId: ' + e))
            entries.append(dict(item=f['itemId'], lo=int(f['minQuantity']), hi=int(f['maxQuantity']), chance=float(f['chance']),
                                pity=int(f['pityAfter']), guarantee=f['guaranteeUntilCollected'] == '1'))
        out[tid] = entries
    return out


class Book:
    def __init__(self, seed, tabs): self.rng, self.misses, self.collected, self.t = Rng(seed), {}, set(), tabs
    def roll(self, tid):
        got = {}
        for e in self.t[tid]:
            if e['guarantee'] and e['item'] not in self.collected: hit = True
            elif e['chance'] >= 1: hit = True
            elif e['chance'] <= 0: continue
            else:
                k = (tid, e['item']); m = self.misses.get(k, 0)
                hit = self.rng.double() < e['chance'] or (e['pity'] > 0 and m >= e['pity'])
                if hit: self.misses.pop(k, None)
                else: self.misses[k] = m + 1
            if not hit: continue
            lo = max(1, e['lo']); hi = max(lo, e['hi'])
            q = lo + (self.rng.int(hi - lo + 1) if hi > lo else 0)
            got[e['item']] = got.get(e['item'], 0) + q
        for i in got: self.collected.add(i)
        return got


HEAPS = ['loot_scrap_heap'] * 6 + ['loot_wreck_carcass'] * 2 + ['loot_drone_wreck']


STRATEGY = 'depot-first'   # or 'heaps-first'
LOSE_DEPOT_DRONE_CACHE = False  # QA run 1: the hover drone's cache was missed / despawned on re-form


def run(seed, tabs):
    b = Book(seed, tabs); pack = {}
    order = random.Random(seed)
    def add(g, table=None):
        if LOSE_DEPOT_DRONE_CACHE and table == 'loot_feral_scrap_drone': return
        for k, v in g.items(): pack[k] = pack.get(k, 0) + v
    add(b.roll('loot_feral_scrap_drone'))
    def clear():
        nest = ['loot_feral_scrap_drone', 'loot_feral_worker_droid', 'loot_feral_worker_droid']; order.shuffle(nest)
        for t in nest: add(b.roll(t), t)
    clear()
    done = lambda: pack.get('micro_capacitor', 0) >= 2 and pack.get('copper_filament', 0) >= 2
    clears = heaps = 0
    if done(): return 0, 0
    for _ in range(20):
        if STRATEGY == 'depot-first' or clears or heaps:
            clears += 1; clear()
            if done(): return clears, heaps
        route = HEAPS[:]; order.shuffle(route)
        for t in route:
            heaps += 1; add(b.roll(t))
            if done(): return clears, heaps
    return clears, heaps


def summary(tabs, n):
    res = [run(random.Random(i).getrandbits(64), tabs) for i in range(n)]
    within = lambda c, h: round(sum(1 for a, b in res if a <= c and b <= h) / n, 3)
    rank = sorted(res, key=lambda x: x[0] * 10 + x[1])  # a depot clear ranks like ~10 heap searches
    return dict(seeds=n, readyAfterPrimer=within(0, 0), within1Clear=within(1, 0), within1ClearPlus3Heaps=within(1, 3),
                within1ClearPlus9Heaps=within(1, 9), needs2ndClear=round(sum(1 for c, h in res if c >= 2) / n, 3),
                median=rank[n // 2], p90=rank[int(n * .9)], worst=rank[-1])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--baseline', default='HEAD'); ap.add_argument('--seeds', type=int, default=20000)
    ap.add_argument('--strategy', default='depot-first', choices=['depot-first', 'heaps-first']); ap.add_argument('--lose-depot-drone-caches', action='store_true')
    a = ap.parse_args()
    STRATEGY = a.strategy; LOSE_DEPOT_DRONE_CACHE = a.lose_depot_drone_caches
    before = tables(subprocess.run(['git', 'show', f'{a.baseline}:{ASSET}'], cwd=REPO, capture_output=True, text=True, check=True).stdout)
    after = tables((REPO / ASSET).read_text())
    print('before', summary(before, a.seeds))
    print('after ', summary(after, a.seeds))

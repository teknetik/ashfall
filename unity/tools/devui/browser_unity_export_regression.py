"""Copy the actual Unity export through Item Lab; no Unity or paid API calls.

Run: uv run --offline --with playwright python unity/tools/devui/browser_unity_export_regression.py
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from model import validate
from server import App, UNITY_CRAFT_EXPORT


def main():
    evidence = Path(__file__).resolve().parents[2] / 'evidence/inventory-redesign-20261002/authoring-export'
    evidence.mkdir(parents=True, exist_ok=True)
    raw = UNITY_CRAFT_EXPORT.read_bytes()
    source = json.loads(raw)
    selected_ids = ['targeting_implant_mk2', 'field_leggings', 'aug_cognition', 'armour_leg_motor']
    items = {x['id']: x for x in source['items']}
    hosts = {x['itemId']: x for x in source['character']['equipment']}
    modules = {x['itemId']: x for x in source['character']['modifications']}
    errors, calls, copied = [], [], []
    with tempfile.TemporaryDirectory(dir=evidence, prefix='isolated-') as folder, patch.dict(os.environ, {'OPENAI_API_KEY': 'offline-regression-key'}):
        root = Path(folder)
        app = App(0, root / 'qa', root / 'draft')

        def refuse_transport(*args):
            calls.append('unexpected provider call')
            raise AssertionError('This regression must not call OpenAI')

        app.authoring.transport = refuse_transport
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(executable_path='/usr/sbin/chromium', headless=True, args=['--no-sandbox'])
                page = browser.new_page(viewport={'width':1536, 'height':1080})
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{app.server_port}/')
                page.locator('[data-tab="items"]').click()
                page.locator('#unityItemSource').wait_for()
                assert page.locator('#unityItemSource option').count() == len(items) == 50
                for item_id, kind in zip(selected_ids, ['implant', 'armour', 'augmentation', 'armour_mod']):
                    page.locator('#unityItemSource').select_option(item_id)
                    page.locator('#copyUnityItem').click()
                    draft = page.evaluate('work.items[selection]')
                    item = items[item_id]
                    authored = hosts.get(item_id, modules.get(item_id))
                    for field in ['id', 'name', 'description', 'weightKg', 'rarity', 'tags', 'buyPrice', 'sellPrice']:
                        assert draft[field] == item[field], (item_id, field, draft[field], item[field])
                    assert draft['stack'] == item['maxStack']
                    assert draft['tier'] == (hosts[item_id]['tier'] if item_id in hosts else 1)
                    equipment = draft['equipment']
                    assert equipment['kind'] == kind
                    assert equipment['slots'] == authored['slots']
                    assert equipment['modifiers'] == authored['modifiers']
                    if kind == 'implant':
                        assert len(equipment['modificationSockets']) == 3
                        assert all(socket['type'] == 'implant' for socket in equipment['modificationSockets'])
                        assert page.locator('.implant-socket-list li').count() == 3
                        page.evaluate('window.scrollTo(0,0)')
                        page.screenshot(path=str(evidence / 'actual-implant-copy.png'), full_page=True)
                    elif kind == 'armour':
                        assert equipment['modificationSockets'] == authored['modificationSockets']
                        assert page.locator('[data-socket-kind="0"]').input_value() == 'armour_motor'
                    else:
                        assert equipment['socketTypes'] == authored['socketTypes']
                    if item_id == 'armour_leg_motor':
                        assert page.locator('[data-effect-percent="0"]').input_value() == '8'
                        assert equipment['modifiers'][0]['percent'] == .08
                        page.evaluate('window.scrollTo(0,0)')
                        page.screenshot(path=str(evidence / 'actual-motor-copy.png'), full_page=True)
                    assert not validate(page.evaluate('work')), validate(page.evaluate('work'))
                    copied.append(deepcopy(draft))
                    page.locator('#save').click()
                    page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                    assert next(x for x in app.draft()[0]['items'] if x['id'] == item_id) == draft

                # User edits are independent of the read-only source snapshot and
                # copying the same ID selects existing draft work without overwrite.
                page.locator('[data-effect-percent="0"]').fill('12')
                page.locator('[data-effect-percent="0"]').press('Tab')
                page.locator('textarea[name="description"]').fill('Local motor review: keep this text.')
                page.locator('textarea[name="description"]').press('Tab')
                modified = page.evaluate('work.items[selection]')
                assert modified['equipment']['modifiers'][0]['percent'] == .12
                assert page.evaluate('unityCraft') == source
                page.locator('#unityItemSource').select_option('armour_leg_motor')
                page.locator('#copyUnityItem').click()
                assert page.evaluate('work.items[selection]') == modified
                assert 'no fields overwritten' in page.locator('#notice').inner_text()
                page.locator('#save').click()
                page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()

                page.locator('#unityItemSource').select_option('field_leggings')
                page.locator('#copyUnityItem').click()
                page.locator('[data-socket-label="0"]').fill('Local motor socket review')
                page.locator('[data-socket-label="0"]').press('Tab')
                assert page.evaluate('unityCraft') == source
                page.locator('#discard').click()
                assert page.locator('[data-socket-label="0"]').input_value() == hosts['field_leggings']['modificationSockets'][0]['label']

                page.reload()
                page.locator('[data-tab="items"]').click()
                page.locator('#unityItemSource').wait_for()
                for item_id in selected_ids:
                    page.locator('#unityItemSource').select_option(item_id)
                    page.locator('#copyUnityItem').click()
                    restored = page.evaluate('work.items[selection]')
                    expected = modified if item_id == 'armour_leg_motor' else next(x for x in copied if x['id'] == item_id)
                    assert restored == expected
                assert not validate(app.draft()[0])
                assert not errors, errors
                assert not calls, calls
                browser.close()
                report = {
                    'result': 'passed', 'source': str(UNITY_CRAFT_EXPORT.relative_to(Path(__file__).resolve().parents[3])),
                    'sourceSha256': hashlib.sha256(raw).hexdigest(), 'exportCounts': {
                        'items': len(items), 'equipment': len(hosts), 'modifications': len(modules)},
                    'copiedActualItems': copied, 'checks': [
                        '50 actual Unity catalogue entries exposed in picker',
                        'Four actual records copy identity, description, prices, weight, rarity, tags and stack',
                        'Host tiers preserved, including Mk.II tier 2 and armour tier 0',
                        'Implant has exactly three augmentation sockets',
                        'Armour socket IDs, labels and types preserved',
                        'Component compatibility and all fractional modifiers preserved',
                        'Motor .08 displays 8 percent and edited 12 percent stores .12',
                        'Editing copied effects and sockets leaves read-only export unchanged',
                        'Recopy selects existing draft without overwriting edits',
                        'Backend validation and disk persistence pass; reload preserves records',
                        'No browser errors; no OpenAI calls; isolated draft and QA directories'],
                    'paidRequests': len(calls), 'browserErrors': errors,
                }
                (evidence / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps({'result': 'passed', 'items': selected_ids, 'evidence': str(evidence)}))
        finally:
            app.shutdown()
            app.server_close()
            thread.join()


if __name__ == '__main__':
    main()

"""Independent local Chromium UI QA against a real integrated Unity development player."""
import json
import http.client
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / 'browser-live'
BASE = 'http://127.0.0.1:8766'
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/sbin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.locator('#connection').get_by_text('LIVE · UNITY').wait_for(timeout=20000)
    assert '38 → 38 points' in page.locator('#view').inner_text()
    assert page.locator('#view tbody tr').count() == 9
    page.screenshot(path=str(OUT / 'live-session.png'), full_page=True)
    checks.append('Visible live session shows actual Unity, nine catalogue IDs, 38 recoil, controls and unavailable weather')
    baseline = page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
    assert baseline['build']['development'] and baseline['source'] == 'unity'
    # Stop polling only in this QA page after proving the form-reset defect.
    # Keep the real HTTP command/ACK path for the remaining checks.
    page.evaluate("refreshLive = async () => {}")
    qty = next(i['quantity'] for i in baseline['items'] if i['id'] == 'scrap_alloy')
    page.locator('select[name="itemId"]').select_option('scrap_alloy')
    page.locator('button[data-command="dev.item.grant"]').click()
    page.get_by_text('Unity acknowledged dev.item.grant').wait_for(timeout=10000)

    now = page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
    assert next(i['quantity'] for i in now['items'] if i['id'] == 'scrap_alloy') == qty + 1
    page.locator('select[name="itemId"]').select_option('scrap_alloy')
    page.locator('button[data-command="dev.item.remove"]').click()
    page.get_by_text('Unity acknowledged dev.item.remove').wait_for(timeout=10000)
    now = page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
    assert next(i['quantity'] for i in now['items'] if i['id'] == 'scrap_alloy') == qty
    checks.append('Visible grant/remove buttons produced correlated native ACK and readback without inventory drift')
    export = page.evaluate("async () => (await (await fetch('/api/unity-crafting')).json()).data")
    assert export['schema'] == 'ward-crafting/1' and len(export['items']) == 9
    assert len(export['recipes']) == 1 and len(export['enemies']) == 2
    page.locator('[data-tab="items"]').click()
    page.get_by_text('DRAFT · NOT IN GAME').first.wait_for()
    page.locator('.record[data-index="1"]').click()
    assert 'LIVE UNITY CATALOGUE · READ ONLY' in page.locator('#editor').inner_text()
    page.screenshot(path=str(OUT / 'item-lab.png'), full_page=True)
    page.locator('.record').filter(has_text='Scrap pistol').click()
    assert 'Design-only ID' in page.locator('#editor').inner_text()
    page.locator('[data-tab="recipes"]').click()
    assert 'Unity Editor export snapshot · ID match only' in page.locator('#editor').inner_text()
    assert 'requires weapon_scrap_pistol' in page.locator('#editor').inner_text()
    page.screenshot(path=str(OUT / 'recipe-lab.png'), full_page=True)
    page.locator('[data-tab="enemies"]').click()
    assert 'Unity Editor export snapshot · ID match only' in page.locator('#editor').inner_text()
    assert 'loot ' in page.locator('#editor').inner_text()
    page.locator('[data-tab="graph"]').click()
    assert 'Draft relationships' in page.locator('#view').inner_text()
    page.screenshot(path=str(OUT / 'graph.png'), full_page=True)
    checks.append('Item, recipe, enemy ID mapping and navigable draft graph display read-only Unity export without claiming draft parity')
    page.locator('[data-tab="items"]').click()
    page.locator('.record[data-index="1"]').click()
    original = page.locator('input[name="name"]').input_value()
    draft_name = 'QA draft servo ' + str(time.time_ns())
    page.locator('input[name="name"]').fill(draft_name)
    page.locator('input[name="name"]').press('Tab')
    assert page.evaluate('dirty') and page.locator('#save').is_disabled()
    checks.append('DEFECT: edited item sets dirty but Save remains disabled until tab rerender')
    page.locator('[data-tab="recipes"]').click()
    page.locator('[data-tab="items"]').click()
    assert page.locator('#save').is_enabled()
    page.locator('#save').click()
    page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
    page.reload()
    page.locator('[data-tab="items"]').click()
    page.locator('.record[data-index="1"]').click()
    assert page.locator('input[name="name"]').input_value() == draft_name
    assert next(i['name'] for i in page.evaluate("async () => (await (await fetch('/api/status')).json()).state")['items'] if i['id'] == 'droid_servo_damaged') != draft_name
    with page.expect_download() as downloaded:
        page.locator('#export').click()
    download = downloaded.value
    download.save_as(OUT / 'ward-draft-export.json')
    draft = json.loads((OUT / 'ward-draft-export.json').read_text())
    assert next(i['name'] for i in draft['items'] if i['id'] == 'droid_servo_damaged') == draft_name
    checks.append('Visible draft edit/save/reload/export persists only draft; live Unity item is unchanged')
    config = page.evaluate("async () => await (await fetch('/api/config')).json()")
    bad = page.evaluate("async () => {let r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'dev.item.grant',itemId:'scrap_alloy',quantity:1})});return r.status}")
    assert bad == 403
    connection = http.client.HTTPConnection('127.0.0.1', 8766, timeout=5)
    connection.request('POST', '/api/command', body='{"action":"dev.state"}', headers={'Origin': 'http://evil.invalid', 'X-Ward-CSRF': config['token'], 'Content-Type': 'application/json'})
    foreign = connection.getresponse().status
    connection.close()
    assert foreign == 403
    invalid = page.evaluate("async token => {let r=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Ward-CSRF':token},body:JSON.stringify({action:'dev.craft'})});return r.status}", config['token'])
    assert invalid == 400
    checks.append('Live web command rejects missing CSRF, foreign Origin and unlisted craft request')
    assert not errors, errors
    (OUT / 'browser-report.json').write_text(json.dumps({'passed': True, 'checks': checks, 'baseline': {'credits': baseline['session']['credits'], 'items': len(baseline['items']), 'recoil': baseline['combat']['recoil']}, 'page_errors': errors, 'screenshots': ['live-session.png', 'item-lab.png', 'recipe-lab.png', 'graph.png']}, indent=2))
    browser.close()
print(json.dumps(checks, indent=2))

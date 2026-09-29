"""Independent Chromium regression against an actual opted-in Unity player."""
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright
from Xlib import X
from Xlib.ext import xtest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / 'browser-live'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
from settings_test_input import focus, key, window

PLAYER = ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'
args = [str(PLAYER), '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1280', '-screen-height', '720', '-logFile', str(OUT/'Player.log'), '--athen-qa', str(OUT/'qa'), '--athen-qa-background']
env = dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':0'), XDG_CONFIG_HOME=str(OUT/'config'))
checks=[]
player=server=None
errors=[]
try:
    with (OUT/'player-launch.log').open('wb') as log:
        player=subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
    os.environ['ATHEN_NATIVE_PID']=str(player.pid)
    os.environ['ATHEN_NATIVE_DIR']=str(OUT/'qa')
    for _ in range(900):
        if player.poll() is not None: raise RuntimeError(f'player exited {player.returncode}')
        snap=OUT/'qa/snapshot.json'
        if snap.exists() and json.loads(snap.read_text())['session']['state']=='MainMenu': break
        time.sleep(.1)
    else: raise TimeoutError('main menu')
    if subprocess.run(['which','hyprctl'],capture_output=True).returncode==0:
        subprocess.run(['hyprctl','-i','0','dispatch',f'hl.dsp.window.float({{action="set",window="pid:{player.pid}"}})'],capture_output=True)
    for _ in range(100):
        try:
            d=focus();w=window(d);break
        except RuntimeError:
            time.sleep(.1)
    else:raise RuntimeError('Native player window did not appear')
    for _ in range(200):
        if json.loads(snap.read_text())['session']['state']=='Play': break
        if _ % 15 == 0:
            d=focus();key(d,'Return',True);time.sleep(.1);key(d,'Return',False)
        time.sleep(.1)
    else: raise TimeoutError('Play')
    server=subprocess.Popen([sys.executable,str(ROOT/'tools/devui/server.py'),'--qa-dir',str(OUT/'qa'),'--draft-dir',str(OUT/'draft'),'--port','8766'],stdout=(OUT/'server.log').open('wb'),stderr=subprocess.STDOUT)
    for _ in range(100):
        if server.poll() is not None: raise RuntimeError(f'server exited {server.returncode}')
        try:
            c=http.client.HTTPConnection('127.0.0.1',8766,timeout=1);c.request('GET','/api/status'); r=c.getresponse();data=json.loads(r.read());c.close()
            if data['status']=='connected':break
        except OSError:pass
        time.sleep(.1)
    else:raise TimeoutError('connected server')
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/sbin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':900},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8766/')
        page.get_by_text('LIVE · UNITY').first.wait_for(timeout=20000)
        state=page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
        assert state['build']['development'] and state['source']=='unity' and len(state['items'])==9
        assert state['combat']['recoil']==38
        page.screenshot(path=str(OUT/'session-before.png'),full_page=True)
        item=page.locator('select[name="itemId"]');item.select_option('scrap_alloy')
        for name,value in [('quantity','4'),('amount','37'),('hour','15.3'),('speed','3.5')]:page.locator(f'input[name="{name}"]').fill(value)
        page.locator('input[name="quantity"]').focus()
        page.wait_for_timeout(3500)
        assert page.locator('#connection').inner_text()=='LIVE · UNITY'
        assert item.input_value()=='scrap_alloy'
        for name,value in [('quantity','4'),('amount','37'),('hour','15.3'),('speed','3.5')]:assert page.locator(f'input[name="{name}"]').input_value()==value
        assert page.evaluate('document.activeElement.name')=='quantity'
        checks.append('Real Unity >3 live polls preserve item ID, quantity, credits, hour, speed and focus')
        before=next(x['quantity'] for x in state['items'] if x['id']=='scrap_alloy')
        page.locator('button[data-command="dev.item.grant"]').click()
        page.get_by_text('Unity acknowledged dev.item.grant').wait_for(timeout=10000)
        latest=page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
        assert next(x['quantity'] for x in latest['items'] if x['id']=='scrap_alloy')==before+4
        assert next(x['quantity'] for x in latest['items'] if x['id']=='water_flask')==next(x['quantity'] for x in state['items'] if x['id']=='water_flask')
        checks.append('Chosen scrap_alloy ID and quantity 4 reached native ACK; water_flask unchanged')
        page.locator('select[name="itemId"]').select_option('scrap_alloy')
        page.locator('button[data-command="dev.item.remove"]').click()
        page.get_by_text('Unity acknowledged dev.item.remove').wait_for(timeout=10000)
        latest=page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
        assert next(x['quantity'] for x in latest['items'] if x['id']=='scrap_alloy')==before
        checks.append('Removal restores starting quantity; no net inventory drift')
        export=page.evaluate("async () => (await (await fetch('/api/unity-crafting')).json()).data")
        assert export['schema']=='ward-crafting/1' and len(export['items'])==9 and len(export['recipes'])==1 and len(export['enemies'])==2
        for tab,expected in [('items','LIVE UNITY CATALOGUE · READ ONLY'),('recipes','Unity Editor export snapshot · ID match only'),('enemies','Unity Editor export snapshot · ID match only')]:
            page.locator(f'[data-tab="{tab}"]').click()
            if tab=='items':page.locator('.record[data-index="1"]').click()
            assert expected in page.locator('#editor').inner_text()
            page.screenshot(path=str(OUT/f'{tab}.png'),full_page=True)
        page.locator('[data-tab="graph"]').click()
        assert 'Draft relationships' in page.locator('#view').inner_text()
        page.screenshot(path=str(OUT/'graph.png'),full_page=True)
        checks.append('Nine Unity items, one recipe, two enemies map read-only; draft graph visible')
        for tab,index in [('items',1),('recipes',0),('enemies',0)]:
            page.locator(f'[data-tab="{tab}"]').click()
            page.locator(f'.record[data-index="{index}"]').click()
            field=page.locator('#editor input[name="name"]')
            name='QA live '+tab+' '+str(time.time_ns())
            field.fill(name);field.press('Tab')
            assert page.evaluate('dirty') and page.locator('#save').is_enabled() and page.locator('#discard').is_enabled()
            page.screenshot(path=str(OUT/f'{tab}-editable.png'),full_page=True)
            page.locator('#save').click()
            page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
            draft=page.evaluate("async () => (await (await fetch('/api/draft')).json()).data")
            assert draft[tab][index]['name']==name
            page.reload();page.locator(f'[data-tab="{tab}"]').click();page.locator(f'.record[data-index="{index}"]').click()
            assert page.locator('#editor input[name="name"]').input_value()==name
            checks.append(f'{tab}: immediate Save/Discard, draft-only persistence after reload')
        with page.expect_download() as download:page.locator('#export').click()
        download.value.save_as(OUT/'draft-export.json')
        assert json.loads((OUT/'draft-export.json').read_text())['enemies'][0]['name']==name
        assert page.evaluate("async () => (await (await fetch('/api/status')).json()).state.items.find(x=>x.id==='droid_servo_damaged').name")!=draft['items'][1]['name']
        checks.append('Export matches saved draft, native item unchanged')
        token=page.evaluate("async () => (await (await fetch('/api/config')).json()).token")
        bad=page.evaluate("async () => (await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status")
        assert bad==403
        bad=page.evaluate("async token => (await fetch('/api/command',{method:'POST',headers:{'X-Ward-CSRF':token,'Content-Type':'application/json'},body:JSON.stringify({action:'dev.craft'})})).status",token)
        assert bad==400
        def request(host,origin,path):
            c=http.client.HTTPConnection('127.0.0.1',8766,timeout=5)
            c.request('POST',path,body='{}',headers={'Host':host,'Origin':origin,'X-Ward-CSRF':token,'Content-Type':'application/json'})
            r=c.getresponse();v=r.status;r.read();c.close();return v
        assert request('127.0.0.1:8766','http://evil.invalid','/api/import')==403
        assert request('evil.invalid','http://127.0.0.1:8766','/api/command')==403
        assert request('127.0.0.1:8766','http://127.0.0.1:8766','/api/unity-crafting')==404
        checks.append('CSRF, Origin, Host, invalid action, POST Unity export refused')
        assert not errors,errors
        browser.close()
    (OUT/'report.json').write_text(json.dumps({'passed':True,'checks':checks,'page_errors':errors,'player_pid':player.pid},indent=2))
    print(json.dumps(checks,indent=2))
finally:
    if server and server.poll() is None:server.terminate();server.wait(timeout=8)
    if player and player.poll() is None:player.terminate();player.wait(timeout=8)

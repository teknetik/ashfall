"""Item Lab authoring UI regression; fake OpenAI transport, no paid calls or Unity mutation.
Run: uv run --offline --with playwright python unity/tools/devui/browser_authoring_regression.py
"""
from io import BytesIO
import base64
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch
import wave

from playwright.sync_api import sync_playwright
from server import App
from test_ai_authoring import COPY, PNG, text_response


def main():
    evidence = Path(__file__).resolve().parents[2] / 'evidence/ui/20261002-developer-authoring'
    evidence.mkdir(parents=True, exist_ok=True)
    calls=[]; errors=[]
    with tempfile.TemporaryDirectory(dir=Path.home()) as folder, patch.dict(os.environ, {'OPENAI_API_KEY':'browser-fixture-key'}):
        root=Path(folder); app=App(0,root/'qa',root/'draft')
        def transport(endpoint,payload,key):
            calls.append(endpoint)
            time.sleep(.15)
            if endpoint=='images/generations':return json.dumps({'data':[{'b64_json':base64.b64encode(PNG).decode()}]}).encode(),'fixture-image'
            if endpoint=='audio/speech':
                out=BytesIO()
                with wave.open(out,'wb') as wav:
                    wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\0\0'*24000)
                return out.getvalue(),'fixture-voice'
            return text_response(COPY if 'text' in payload else 'Courier knee drive\nA compact actuator reclaimed from sorting machinery. Proposed mechanic: improves sprint speed at a stamina cost.\n\nPorous filter lining\nA replaceable filter cartridge with a folded cloth sheath. Proposed mechanic: exchanges protection for easier field maintenance.')
        app.authoring.transport=transport
        thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as runtime:
                browser=runtime.chromium.launch(executable_path='/usr/sbin/chromium',headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1536,'height':1080})
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{app.server_port}/')
                page.locator('[data-tab="items"]').click()
                page.locator('.record[data-index="1"]').click()
                page.locator('#itemAiBrief').fill('A practical servo repaired for a Ward courier.')
                page.locator('#generateItemCopy').click()
                page.locator('#applyItemCopy').wait_for()
                assert page.locator('#editor input[name="name"]').input_value()!='Rebuilt servo'
                assert page.locator('#editor textarea[name="description"]').input_value()==''
                # Editing after generation keeps the comparison accurate without
                # disturbing the deliberate field selections.
                page.locator('[data-apply-field="designNotes"]').uncheck()
                page.locator('#editor textarea[name="description"]').fill('Hand-written review in progress.')
                page.locator('#editor textarea[name="description"]').press('Tab')
                assert page.locator('[data-current-field="description"]').inner_text()=='Hand-written review in progress.'
                assert not page.locator('[data-apply-field="designNotes"]').is_checked()
                page.locator('[data-apply-field="designNotes"]').check()
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(evidence/'item-copy-desktop-fixture.png'),full_page=True)
                page.locator('#applyItemCopy').click()
                assert page.locator('#editor input[name="name"]').input_value()!='Rebuilt servo'
                assert page.locator('#editor textarea[name="description"]').input_value()==COPY['description']
                page.locator('#save').click(); page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                assert app.draft()[0]['items'][1]['description']==COPY['description']
                # Implants always expose three sockets, authored by the structured controls.
                page.locator('#equipmentKind').select_option('implant')
                page.locator('[data-equip-slot="implant_legs"]').check()
                assert page.locator('.implant-socket-list li').count()==3
                page.locator('#addEquipmentEffect').click()
                page.locator('[data-effect-stat="0"]').fill('movementSpeed')
                page.locator('[data-effect-percent="0"]').fill('8');page.locator('[data-effect-percent="0"]').press('Tab')
                assert page.evaluate('work.items[1].equipment.modifiers[0].percent')==.08
                page.locator('#save').click();page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                assert len(app.draft()[0]['items'][1]['equipment']['modificationSockets'])==3
                page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(evidence/'implant-authoring-desktop-fixture.png'),full_page=True)
                # Armour components support type changes and zero-loss fractional effects.
                page.locator('#equipmentKind').select_option('armour')
                page.locator('[data-equip-slot="armour_legs"]').check()
                page.locator('#addArmourSocket').click()
                page.locator('[data-socket-kind="0"]').select_option('armour_motor')
                page.locator('[data-socket-label="0"]').fill('Drive motor');page.locator('[data-socket-label="0"]').press('Tab')
                page.locator('#save').click();page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                assert app.draft()[0]['items'][1]['equipment']['modificationSockets'][0]['type']=='armour_motor'
                page.locator('#generateItemIcon').click();page.locator('#applyItemIcon').wait_for();page.locator('#applyItemIcon').click()
                assert page.locator('.selected-item-art img').count()==1
                page.locator('#save').click();page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                assert app.draft()[0]['items'][1]['iconAsset'].endswith('.png')
                # Creative text and voice use the same journal and never mutate the draft.
                page.locator('[data-tab="creative"]').click();page.locator('#creativeBrief').fill('Courier implants with meaningful tradeoffs.')
                page.locator('#generateCreative').click();page.locator('#copyIdeas').wait_for()
                assert 'ready for review' in page.locator('#notice').inner_text()
                assert '3 records' in page.locator('#generationCount').inner_text()
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(evidence/'creative-desk-desktop-fixture.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844});page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(evidence/'creative-desk-mobile-fixture.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'mobile overflow'
                page.locator('[data-creative-mode="voice"]').click();page.locator('#creativeSpeech').fill('Water first. Then we can talk about the road.')
                page.locator('#generateCreative').click();page.locator('audio').wait_for()
                assert page.locator('audio').get_attribute('src').endswith('.wav')
                assert page.locator('#creativeReview').inner_text().count('AI-generated voice')==1
                page.set_viewport_size({'width':1536,'height':1080});page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(evidence/'voice-audition-desktop-fixture.png'),full_page=True)
                # Reload retains provenance/history and draft attachments; never credentials.
                page.reload();page.locator('[data-tab="creative"]').click();page.locator('.journal-row').first.wait_for()
                assert page.locator('.journal-row').count()==4
                assert 'browser-fixture-key' not in page.content()
                assert not errors,errors
                assert calls==['responses','images/generations','responses','audio/speech'],calls
                browser.close()
                print('PASS: proposal is review-only; selective apply/save; exactly three implant sockets; armour socket editing; 8% -> .08; icon attachment; ideas; voice preview; journal reload; no secrets, page errors or mobile overflow.')
                print('Screenshots are mocked-provider UI evidence:',evidence)
        finally:app.shutdown();app.server_close();thread.join()

if __name__=='__main__':main()

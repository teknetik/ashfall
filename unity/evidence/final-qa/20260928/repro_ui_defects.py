"""Focused non-mutating repro of live Session and Item Lab form retention."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(__file__).parent/'browser-live'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/sbin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':900})
 page.goto('http://127.0.0.1:8766/')
 page.get_by_text('LIVE · UNITY').first.wait_for()
 select=page.locator('select[name="itemId"]')
 select.select_option('scrap_alloy')
 selected_before=select.input_value()
 page.wait_for_timeout(3200)
 selected_after=page.locator('select[name="itemId"]').input_value()
 print('selection',selected_before,selected_after,'status',page.locator('#connection').inner_text())
 assert selected_before=='scrap_alloy' and selected_after=='water_flask'
 page.locator('[data-tab="items"]').click()
 page.locator('.record[data-index="1"]').click()
 input=page.locator('input[name="name"]')
 original=input.input_value();input.fill(original+' QA unsaved');input.press('Tab')
 dirty=page.evaluate('dirty');save_disabled=page.locator('#save').is_disabled()
 assert dirty and save_disabled
 page.screenshot(path=str(out/'unsaved-disabled.png'),full_page=True)
 (out/'defect-repro.json').write_text(json.dumps({'session_item_selection_before':selected_before,'session_item_selection_after_3200ms':selected_after,'item_lab_dirty':dirty,'save_disabled':save_disabled,'draft_mutated_on_disk':False},indent=2))
 print((out/'defect-repro.json').read_text())
 b.close()

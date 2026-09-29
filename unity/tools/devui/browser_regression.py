"""Isolated Chromium regression against the real loopback server and a test-only bridge fixture.

Run: uv run --with playwright python unity/tools/devui/browser_regression.py
This is NOT native Unity acceptance; final QA must repeat against a development player.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server import App


state = {
    'schemaVersion': 1, 'source': 'unity', 'available': True,
    'build': {'development': True, 'version': 'isolated-browser-fixture'},
    'session': {'state': 'Ready', 'objective': 'Test', 'credits': 17},
    'combat': {'available': False}, 'tutorial': {'available': False},
    'clock': {'available': True, 'hour': 12.5, 'speed': 2, 'paused': False},
    'crafting': {'available': False},
    'items': [{'id': 'water_flask', 'name': 'Water flask', 'quantity': 2},
              {'id': 'scrap_alloy', 'name': 'Scrap alloy', 'quantity': 3}],
    'encounters': [],
}


def main():
    with tempfile.TemporaryDirectory(dir=Path.home()) as folder:
        root = Path(folder)
        app = App(0, root / 'qa', root / 'draft')
        path = app.qa / 'dev-state.json'
        path.write_text(json.dumps(state))
        stop = threading.Event()
        commands = []

        def bridge():
            while not stop.wait(.1):
                os.utime(path, None)
                command_path = app.qa / 'command.json'
                if command_path.exists():
                    cmd = json.loads(command_path.read_text())
                    command_path.unlink()
                    commands.append(cmd)
                    (app.qa / 'ack.json').write_text(json.dumps({'id': cmd['id'], 'success': True}))

        server_thread = threading.Thread(target=app.serve_forever, daemon=True)
        bridge_thread = threading.Thread(target=bridge, daemon=True)
        server_thread.start()
        bridge_thread.start()
        errors = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path='/usr/sbin/chromium', headless=True, args=['--no-sandbox'])
                page = browser.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{app.server_port}/')
                page.get_by_text('LIVE · UNITY').first.wait_for()
                item = page.locator('select[name="itemId"]')
                item.select_option('scrap_alloy')
                for name, value in [('quantity', '4'), ('amount', '37'), ('hour', '15.3'), ('speed', '3.5')]:
                    page.locator(f'input[name="{name}"]').fill(value)
                page.locator('input[name="quantity"]').focus()
                page.wait_for_timeout(3400)
                assert page.locator('#connection').inner_text() == 'LIVE · UNITY'
                assert item.input_value() == 'scrap_alloy'
                for name, value in [('quantity', '4'), ('amount', '37'), ('hour', '15.3'), ('speed', '3.5')]:
                    assert page.locator(f'input[name="{name}"]').input_value() == value
                assert page.evaluate('document.activeElement.name') == 'quantity'
                page.locator('button[data-command="dev.item.grant"]').click()
                page.get_by_text('Unity acknowledged dev.item.grant').wait_for()
                assert len(commands) == 1 and commands[0]['itemId'] == 'scrap_alloy' and commands[0]['quantity'] == 4, commands
                assert item.input_value() == 'scrap_alloy'
                # Catalogue disappears while the page is live: never silently target the first item.
                state['items'] = state['items'][:1]
                path.write_text(json.dumps(state))
                page.wait_for_timeout(1200)
                assert item.input_value() == 'scrap_alloy' and page.locator('button[data-command="dev.item.grant"]').is_disabled()
                item.select_option('water_flask')
                assert page.locator('button[data-command="dev.item.grant"]').is_enabled()
                for tab, name, value in [('items', 'name', 'Browser item'),
                                         ('recipes', 'name', 'Browser recipe'),
                                         ('enemies', 'name', 'Browser enemy')]:
                    page.locator(f'[data-tab="{tab}"]').click()
                    editor = page.locator(f'#editor input[name="{name}"]')
                    editor.fill(value)
                    editor.press('Tab')
                    assert page.evaluate('dirty')
                    assert page.locator('#save').is_enabled() and page.locator('#discard').is_enabled()
                    assert editor.input_value() == value
                    # Save immediately, without a tab switch, then check server persistence.
                    page.locator('#save').click()
                    page.get_by_text('Draft saved. Nothing changed in Unity.').wait_for()
                    stored, _ = app.draft()
                    assert stored[tab][0]['name'] == value
                    assert page.locator('#save').is_disabled() and page.locator('#discard').is_disabled()
                # Scalar recipe/enemy paths must not tear down the editor on blur.
                page.locator('[data-tab="recipes"]').click()
                field = page.locator('#editor input[name="seconds"]')
                field.fill('7')
                field.press('Tab')
                assert field.input_value() == '7' and page.locator('#save').is_enabled()
                page.locator('#discard').click()
                page.locator('[data-tab="enemies"]').click()
                loot = page.locator('#editor input[name="loot-chance-0"]')
                loot.fill('52')
                loot.press('Tab')
                assert loot.input_value() == '52' and page.locator('#save').is_enabled()
                page.locator('#discard').click()
                page.reload()
                page.locator('[data-tab="items"]').click()
                assert page.locator('#editor input[name="name"]').input_value() == 'Browser item'
                page.locator('[data-tab="recipes"]').click()
                assert page.locator('#editor input[name="name"]').input_value() == 'Browser recipe'
                page.locator('[data-tab="enemies"]').click()
                assert page.locator('#editor input[name="name"]').input_value() == 'Browser enemy'
                assert not errors, errors
                browser.close()
            print('PASS: >3 polls retain session values/focus; exact command ID/quantity; missing catalogue ID blocked; item/recipe/enemy immediate Save/Discard and server persistence; scalar edits stable; no page errors')
        finally:
            stop.set()
            app.shutdown()
            app.server_close()
            server_thread.join()
            bridge_thread.join()


if __name__ == '__main__':
    main()

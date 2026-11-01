"""Capture the actual post-fit developer UI while the native crafting run is alive."""
from pathlib import Path

HERE=Path(__file__).parent
source=Path('/home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/check_crafting.py')
text=source.read_text()
text=text.replace("OUT = Path(__file__).parent / 'native-smoke'", "OUT = Path("+repr(str(HERE/'postfit-native-attempt3'))+")")
anchor="            report['post_fit']={'quantities':snap()['session']['quantities'],'crafting':craft()}"
assert anchor in text
injection='''            import threading
            from playwright.async_api import async_playwright
            sys.path.insert(0, str(ROOT / 'tools/devui'))
            from server import App
            app=App(0, OUT, OUT/'draft')
            thread=threading.Thread(target=app.serve_forever,daemon=True)
            thread.start()
            try:
                async with async_playwright() as playwright:
                    browser=await playwright.chromium.launch(executable_path='/usr/sbin/chromium',headless=True,args=['--no-sandbox'])
                    page=await browser.new_page(viewport={'width':1440,'height':900})
                    errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    await page.goto(f'http://127.0.0.1:{app.server_port}/')
                    await page.get_by_text('LIVE · UNITY').first.wait_for(timeout=20000)
                    live=await page.evaluate("async () => (await (await fetch('/api/status')).json()).state")
                    assert live['crafting']['gripSlot']=='grip_stabilised_pistol'
                    assert live['combat']['baseRecoil']==38 and live['combat']['recoil']==31
                    assert '38 → 31 points' in await page.locator('#view').inner_text()
                    await page.screenshot(path=str(OUT/'postfit-live.png'),full_page=True)
                    assert not errors, errors
                    report['postfit_ui']={'baseRecoil':38,'recoil':31,'gripSlot':live['crafting']['gripSlot'],'page_errors':errors,'screenshot':'postfit-live.png'}
                    report['checks'].append('Live Chromium shows native post-fit 38→31 recoil and equipped grip with no page errors')
                    await browser.close()
            finally:
                app.shutdown();app.server_close();thread.join()
'''
text=text.replace(anchor,anchor+'\n'+injection.rstrip(),1)
fake=HERE.parent.parent/'crafting/20260928/check_crafting.py'
exec(compile(text,str(source),'exec'),{'__file__':str(fake),'__name__':'__main__'})

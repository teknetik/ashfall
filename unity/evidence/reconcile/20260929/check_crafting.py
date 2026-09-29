"""Run the integrated candidate's native crafting smoke with real keyboard verbs.

This adapts the independently passing crafting-lane harness: only the evidence
output path changes; Unity binary and tool imports resolve from this worktree.
"""
from pathlib import Path


source = Path('/home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/check_crafting.py')
text = source.read_text().replace("OUT = Path(__file__).parent / 'native-smoke'", "OUT = Path(" + repr(str(Path(__file__).parent / 'crafting-native')) + ")")
anchor = "            report['post_fit']={'quantities':snap()['session']['quantities'],'crafting':craft()}"
probe = '''            import sys
            sys.path.insert(0, str(ROOT / 'tools/devui'))
            from server import App
            app = App(0, OUT, OUT / 'draft')
            try:
                import time as _t
                # dev-state.json refreshes every 0.5 s; poll until the fit is reflected (adds a wait, no other change)
                for _i in range(40):
                    status = app.status()
                    if status['status'] == 'connected' and status['state']['crafting'].get('gripSlot'): break
                    _t.sleep(.1)
                assert status['status'] == 'connected', status
                state = status['state']
                assert len(state['items']) == 9 and state['crafting']['gripSlot'] == 'grip_stabilised_pistol', state
                assert state['crafting']['lootEvents'] == 4 and state['crafting']['crafts'] == 1, state
                assert state['combat']['baseRecoil'] == 38 and state['combat']['recoil'] == 31, state
                assert next(x for x in state['items'] if x['id'] == 'grip_stabilised_pistol')['quantity'] == 0
                report['dev_state_after_fit'] = dict(crafting=state['crafting'], combat=state['combat'], items=len(state['items']))
                report['checks'].append('Real development bridge/server reads native fitted grip, loot, 9 items and 38→31 recoil')
            finally: app.server_close()
'''
assert anchor in text
text = text.replace(anchor, anchor + '\n' + probe.rstrip(), 1)
exec(compile(text, str(source), 'exec'), {'__file__': str(Path(__file__).resolve().parents[2] / 'crafting/20260928/check_crafting.py'), '__name__': '__main__'})

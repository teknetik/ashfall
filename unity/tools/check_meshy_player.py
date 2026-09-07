"""Live Editor player replacement smoke check using real keyboard input."""
import asyncio
import json
from pathlib import Path
import shutil
from fastmcp import Client
from desktop_input import focus, key

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/meshy'
CAP = ROOT / 'AthenHill/Captures'

async def main():
    d = focus()
    async with Client('http://127.0.0.1:18081/mcp', timeout=60) as c:
        async def execute(code):
            result = await c.call_tool('execute_code', {'action': 'execute', 'code': code})
            payload = json.loads(result.content[0].text)
            assert payload.get('success'), payload
            return payload['data']['result']
        await execute('var p=UnityEngine.Object.FindAnyObjectByType<AthenHill.PlayerMotor>();p.enabled=true;p.ReturnToGate();UnityEngine.Object.FindAnyObjectByType<AthenHill.GameSession>().Close();UnityEngine.Object.FindAnyObjectByType<AthenHill.FollowCamera>().yaw=-90;UnityEditor.EditorWindow.GetWindow(System.Type.GetType("UnityEditor.GameView,UnityEditor")).Focus();return true;')
        await asyncio.sleep(.5)
        evidence = []
        try:
            for name in ['idle', 'walk', 'run', 'idle-return']:
                key(d, 'w', name in ['walk', 'run'])
                key(d, 'Shift_L', name == 'run')
                await asyncio.sleep(.6)
                row = await execute('var p=UnityEngine.Object.FindAnyObjectByType<AthenHill.PlayerMotor>();var cam=UnityEngine.GameObject.Find("character").GetComponent<UnityEngine.Camera>();cam.transform.position=p.transform.position+p.visual.forward*3.6f-p.visual.right*1.3f+UnityEngine.Vector3.up*1.2f;cam.transform.LookAt(p.transform.position+UnityEngine.Vector3.up*.95f);AthenHill.Editor.PortDiagnostics.Capture("character");AthenHill.Editor.PortDiagnostics.Snapshot();return new {play=UnityEditor.EditorApplication.isPlaying,clip=p.actor.CurrentClip,speed=p.Speed,grounded=p.Grounded,position=p.transform.position.ToString(),time=p.actor.animationSource[p.actor.CurrentClip].time};')
                assert row['play'] and row['grounded'], row
                assert row['clip'] == ('idle' if name == 'idle-return' else name), row
                if name in ['walk', 'run']: assert row['speed'] > 3 and row['time'] > 0, row
                shutil.copyfile(CAP/'Fixed/character.png', OUT/f'{name}.png')
                shutil.copyfile(CAP/'snapshot.json', OUT/f'{name}.json')
                evidence.append({'step': name, **row})
                print(evidence[-1], flush=True)
        finally:
            key(d, 'w', False)
            key(d, 'Shift_L', False)
        assert evidence[2]['speed'] > evidence[1]['speed'], evidence
        (OUT/'animation-check.json').write_text(json.dumps(evidence, indent=2))

asyncio.run(main())

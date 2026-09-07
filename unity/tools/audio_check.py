"""Capture only Unity's audio using a temporary dedicated PulseAudio sink."""
import asyncio,json,pathlib,subprocess,wave,math,array
from fastmcp import Client
from desktop_input import focus,key
R=pathlib.Path(__file__).resolve().parents[1];C=R/'AthenHill/Captures';O=R/'evidence/U4/audio';O.mkdir(parents=True,exist_ok=True)
def command(*args):return subprocess.check_output(args,text=True).strip()
async def main():
 inputs=json.loads(command('pactl','-f','json','list','sink-inputs'));stream=next(x for x in inputs if x['properties'].get('application.process.binary')=='Unity');old=stream['sink'];sid=stream['index'];module=command('pactl','load-module','module-null-sink','sink_name=athen_qa','sink_properties=device.description=AthenQA');command('pactl','move-sink-input',str(sid),'athen_qa')
 checks=[];d=focus()
 try:
  async with Client('http://127.0.0.1:18081/mcp',timeout=60) as c:
   await c.call_tool('set_active_instance',{'instance':'AthenHill@7f7f353bae1a07d0'})
   async def snap():
    await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Write snapshot'});return json.loads((C/'snapshot.json').read_text())
   async def tap(name,duration=.08):
    key(d,name,True)
    try:await asyncio.sleep(duration)
    finally:key(d,name,False)
    await asyncio.sleep(.2)
   async def button(name):
    for i in range(30):
     if (await snap())['session']['focused']==name:await tap('Return');return
     await tap('Tab')
    raise RuntimeError('Focus not found '+name)
   async def record(name,duration=3,walk=False):
    path=O/(name+'.wav');p=await asyncio.create_subprocess_exec('/usr/bin/ffmpeg','-hide_banner','-loglevel','error','-y','-f','pulse','-i','athen_qa.monitor','-t',str(duration),'-ar','48000','-ac','2',str(path))
    if walk:await tap('w',duration-.3)
    assert await p.wait()==0
    with wave.open(str(path)) as w:values=array.array('h',w.readframes(w.getnframes()))
    rms=math.sqrt(sum(float(x)*x for x in values)/len(values))/32768;peak=max(abs(x) for x in values)/32768
    s=await snap();checks.append({'name':name,'rms':rms,'peak':peak,'audio':s['audio'],'state':s['session']['state']});(O/'report.json').write_text(json.dumps(checks,indent=2));print(name,rms,peak,flush=True);return checks[-1]
   if (await snap())['session']['state']=='Paused':await tap('Escape')
   s=await record('ambience',13);assert s['rms']>.0001
   s=await record('footsteps',4,True);assert s['audio']['StepCount']>2
   (C/'debug-command.json').write_text(json.dumps({'action':'goto','landmark':'lattice_jack'}));await c.call_tool('execute_menu_item',{'menu_path':'Athen Hill/Diagnostics/Apply command'});await asyncio.sleep(.5)
   s=await record('spatial-hum',6);assert s['audio']['sources']
   await tap('e');s=await record('lattice-confirmation',2);assert s['audio']['ClickCount']>0
   await tap('Escape');await tap('Escape');await asyncio.sleep(.6);s=await record('paused',2);assert s['rms']<.00001 and s['audio']['listenerPaused']
   await button('mute');await button('resume');await asyncio.sleep(.6);s=await record('muted',2);assert s['rms']<.00001 and s['audio']['listenerVolume']==0
   await tap('Escape');await button('mute');await button('resume');s=await record('restored',2);assert s['rms']>.0001
   print('PASS: Unity ambience, footsteps, spatial hum, UI confirmation, pause/mute and restoration')
 finally:
  command('pactl','move-sink-input',str(sid),str(old));command('pactl','unload-module',module)
asyncio.run(main())

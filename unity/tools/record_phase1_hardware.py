"""Sample this QA player's process memory without exposing other app details."""
import datetime,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
O=Path(sys.argv[1]);pid=(O/'pid').read_text().strip();xml=ET.fromstring(subprocess.check_output(['nvidia-smi','-q','-x'],text=True));gpu=xml.find('gpu')
proc=next((p for p in xml.findall('.//process_info') if p.findtext('pid')==pid),None)
def mib(v):
 try:return int(v.split()[0])*1024*1024
 except (AttributeError,ValueError):return None
memory={line.split(':')[0]:line.split(':',1)[1].strip() for line in Path('/proc/'+pid+'/status').read_text().splitlines() if line.startswith(('VmRSS:','VmHWM:','VmSize:'))}
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),nativeProcess=int(pid),gpu=gpu.findtext('product_name'),driver=xml.findtext('driver_version'),vramBytes=mib(gpu.findtext('fb_memory_usage/total')),nativeGpuMemoryBytes=mib(proc.findtext('used_memory')) if proc is not None else None,nativeMemory=memory,residentTextureBytes=None,residentTextureNote='Existing bridge does not expose texture residency. GPU process allocation includes more than textures.',hostMemory=next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')),api='OpenGLCore',renderScale=1,resolution=[1920,1080],frameGeneration=False)
r['editorClosed']=not any('/Editor/Unity -projectPath /home/teknetik/code/ao2/unity/AthenHill' in x for x in subprocess.check_output(['ps','-eo','comm,args'],text=True).splitlines() if x.strip().startswith('Unity '))
(O/'hardware.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))

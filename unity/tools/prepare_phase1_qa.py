"""Restore requested client dimensions after the window manager's initial tiling."""
import asyncio,json,os,sys
from pathlib import Path
from native_client import Client
from desktop_input import focus
O=Path(sys.argv[1]).resolve();os.environ.update(ATHEN_NATIVE_DIR=str(O),ATHEN_NATIVE_PID=(O/'pid').read_text().strip())
async def main():
 d=focus();c=Client()
 def snap():return json.loads((O/'snapshot.json').read_text())
 before=snap()
 if (before['width'],before['height'])!=(1920,1080):
  await c.command({'action':'resize','width':1920,'height':1080});await asyncio.sleep(1.2)
 current=snap();assert (current['width'],current['height'])==(1920,1080)
 await c.command({'action':'settingsSnapshot'})
 settings=json.loads((O/'settings.json').read_text());assert settings['renderScale']==1
 if '--uncapped' in sys.argv:assert settings['vSync']==0 and settings['frameLimit']==-1
 (O/'viewport.json').write_text(json.dumps(dict(initial=[before['width'],before['height']],measured=[current['width'],current['height']],settings=settings),indent=2))
 print(json.dumps(dict(width=current['width'],height=current['height'],frameLimit=settings['frameLimit'],vSync=settings['vSync'])))
asyncio.run(main())

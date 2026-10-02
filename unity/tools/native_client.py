"""Reuse real-keyboard checks against an explicitly enabled development player."""
import asyncio,json,os,pathlib,time,uuid
class Client:
 def __init__(self,*args,**kwargs):self.folder=pathlib.Path(os.environ['ATHEN_NATIVE_DIR'])
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 async def command(self,j):
  j=dict(j,id=uuid.uuid4().hex);tmp=self.folder/'command.tmp';tmp.write_text(json.dumps(j));tmp.rename(self.folder/'command.json')
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   p=self.folder/'ack.json'
   if p.exists():
    ack=json.loads(p.read_text())
    if ack.get('id')==j['id']:
     if not ack.get('success'):raise RuntimeError('Native QA rejected command: '+str(ack.get('error')))
     await asyncio.sleep(.15);return
   await asyncio.sleep(.02)
  raise TimeoutError('Native QA command was not acknowledged: '+str(j))
 async def snapshot(self):
  """Read focus/state from a frame after an acknowledged, read-only QA command."""
  path=self.folder/'snapshot.json'
  try:previous=json.loads(path.read_text())['frame']
  except (FileNotFoundError,json.JSONDecodeError):previous=-1
  await self.command({'action':'uiSnapshot'})
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   try:
    value=json.loads(path.read_text())
    if value['frame']>previous:return value
   except (FileNotFoundError,json.JSONDecodeError):pass
   await asyncio.sleep(.03)
  raise TimeoutError('No fresh native QA snapshot after frame '+str(previous))
 async def call_tool(self,name,args):
  if name=='set_active_instance':return
  if name=='execute_menu_item':
   menu=args['menu_path']
   if menu.endswith('Write snapshot'):await asyncio.sleep(.12);return
   if menu.endswith('Apply command'):await self.command(json.loads((self.folder/'debug-command.json').read_text()));return
  if name=='manage_camera' and args['action']=='screenshot':await self.command({'action':'capture','name':args['screenshot_file_name']});return
  raise ValueError('Unsupported native test operation '+name+str(args))


async def select_merchant_item(client, item_id, tap):
 """Select a stock row using real Tab/arrows; only the selected row is a Tab stop.

 The caller then Tabs to merchant-trade, which must retain this selected item.
 Snapshot commands are read-only; no UI or gameplay action goes through the bridge.
 """
 def read(name):
  for _ in range(20):
   try:return json.loads((client.folder/name).read_text())
   except (FileNotFoundError,json.JSONDecodeError):time.sleep(.05)
  raise RuntimeError('Unreadable native QA '+name)
 await client.command({'action':'uiSnapshot'})
 rows=[e['name'] for e in read('ui-layout.json')['elements'] if e.get('visible') and e.get('enabled') and (e.get('name') or '').startswith('merchant-item-')]
 target='merchant-item-'+item_id
 if target not in rows:raise RuntimeError('Merchant stock row absent: '+target)
 for _ in range(40):
  focused=(await client.snapshot())['session']['focused']
  if focused in rows:break
  await tap('Tab')
 else:raise RuntimeError('Could not keyboard-focus merchant stock')
 direction='Down' if rows.index(target)>rows.index(focused) else 'Up'
 for _ in range(abs(rows.index(target)-rows.index(focused))):await tap(direction)
 focused=(await client.snapshot())['session']['focused']
 if focused!=target:raise RuntimeError('Merchant arrows focused %r, expected %r'%(focused,target))
 await tap('Return')

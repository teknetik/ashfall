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
   if p.exists() and json.loads(p.read_text())['id']==j['id']:
    await asyncio.sleep(.15);return
   await asyncio.sleep(.02)
  raise TimeoutError('Native QA command was not acknowledged: '+str(j))
 async def call_tool(self,name,args):
  if name=='set_active_instance':return
  if name=='execute_menu_item':
   menu=args['menu_path']
   if menu.endswith('Write snapshot'):await asyncio.sleep(.12);return
   if menu.endswith('Apply command'):await self.command(json.loads((self.folder/'debug-command.json').read_text()));return
  if name=='manage_camera' and args['action']=='screenshot':await self.command({'action':'capture','name':args['screenshot_file_name']});return
  raise ValueError('Unsupported native test operation '+name+str(args))

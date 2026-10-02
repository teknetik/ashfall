"""Resumable Meshy source generation. No credential values are printed or persisted."""
import argparse,json,os,re,subprocess,urllib.request,urllib.error
from pathlib import Path
HERE=Path(__file__).resolve().parent
def credential_file(explicit=None):
 """Find credentials beside this checkout or in its primary Git worktree."""
 if explicit is not None:
  return Path(explicit).expanduser().resolve()
 root=HERE.parents[1]
 local=root/'.env'
 if local.is_file():
  return local
 try:
  result=subprocess.run(['git','-C',str(root),'rev-parse','--git-common-dir'],capture_output=True,text=True,check=True)
  common=Path(result.stdout.strip())
  if not common.is_absolute():
   common=root/common
  candidate=common.resolve().parent/'.env'
  if candidate.is_file():
   return candidate
 except (OSError,subprocess.CalledProcessError):
  pass
 return local

def load_key(explicit=None):
 # An explicit file takes precedence. Otherwise standard process configuration wins.
 if explicit is None and os.environ.get('MESHY_API_KEY','').strip():
  return os.environ['MESHY_API_KEY'].strip()
 try:
  lines=credential_file(explicit).read_text().splitlines()
 except OSError:
  raise RuntimeError('MESHY_API_KEY not configured; set it in the environment or pass --env-file.') from None
 for line in lines:
  match=re.match(r'\s*(?:export\s+)?MESHY_API_KEY\s*=\s*(.*?)\s*$',line)
  if match:
   value=match.group(1)
   if value[:1] in ('"', "'"):
    quote=value[0]
    end=value.find(quote,1)
    if end<0:
     continue
    value=value[1:end]
   else:
    value=re.split(r'\s+#',value,maxsplit=1)[0].strip()
   if value:
    return value
 raise RuntimeError('MESHY_API_KEY not configured in the selected environment file.')

key=''
BASE='https://api.meshy.ai/openapi/v2/text-to-3d'
def api(method,path='',payload=None):
 req=urllib.request.Request(BASE+path,data=json.dumps(payload).encode() if payload else None,method=method,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return json.load(r)
 except urllib.error.HTTPError as e:raise RuntimeError('Meshy HTTP '+str(e.code)) from None
prompt='One realistic handmade science-fiction field rifle for a desert colony, 0.9 metres long, a shoulder-fired carbine built from repaired industrial steel parts. Clear long straight ribbed barrel with open round muzzle, chunky bolted receiver, compact detachable box magazine, slanted leather-wrapped pistol grip with open trigger guard, skeletal solid shoulder stock with rubber buttpad, low iron sights and mounting rail. Distinct barrel, receiver, trigger guard, magazine and stock. Faint cyan charge cell inset into receiver, worn gunmetal, warm grey painted metal, copper connectors, dark rubber and leather. Hard-surface engineering, convincing construction, restrained weathering at seams and handles. Single isolated object, no hands, no people, no base, no text, no logos.'
def main(argv=None):
 global key
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('mode',choices=('start','preview','texture','refine'))
 parser.add_argument('--env-file',help='Read MESHY_API_KEY from this file. Otherwise use the process environment, checkout .env, or primary Git worktree .env.')
 args=parser.parse_args(argv)
 try:
  key=load_key(args.env_file)
 except RuntimeError as error:
  parser.error(str(error))
 mode=args.mode
 file=HERE/'manifest.json'
 m=json.loads(file.read_text()) if file.exists() else {'asset':'Ward Field Rifle','dimensions_m':{'length':.9},'closest_view_m':.3,'purpose':'Primary weapon inventory inspect mesh','prompt':prompt,'format':'glb','credits':'unknown','source_detail_retained':True,'tasks':{}}
 def save():file.write_text(json.dumps(m,indent=2)+'\n')
 if mode=='start':
  if 'preview' not in m['tasks']:
   options={'mode':'preview','prompt':prompt,'ai_model':'latest','should_remesh':True,'target_polycount':30000,'topology':'triangle','target_formats':['glb'],'alpha_thumbnail':True}
   response=api('POST',payload=options);m['tasks']['preview']=response['result'];m['preview_options']=options;save()
  print('Preview task:',m['tasks']['preview'],flush=True)
 elif mode in ('preview','refine'):
  task=m['tasks'][mode];r=api('GET','/'+task);(HERE/(mode+'-status.json')).write_text(json.dumps(r,indent=2)+'\n');print(mode,r['status'],r.get('progress'),flush=True)
  if r['status']=='SUCCEEDED':
   for name,url in [(mode+'.glb',r.get('model_urls',{}).get('glb')),(mode+'.png',r.get('thumbnail_url')),(mode+'-alpha.png',r.get('alpha_thumbnail_url')),(mode+'-source.glb',r.get('model_urls',{}).get('pre_remeshed_glb'))]:
    if url and not (HERE/name).exists():
     with urllib.request.urlopen(url,timeout=120) as f:(HERE/name).write_bytes(f.read())
   m[mode+'_status']='SUCCEEDED';m[mode+'_credits']=r.get('consumed_credits','unknown');save()
 elif mode=='texture':
  if 'refine' not in m['tasks']:
   options={'mode':'refine','preview_task_id':m['tasks']['preview'],'ai_model':'latest','enable_pbr':True,'texture_prompt':'Desert colony salvaged rifle: realistic weathered gunmetal receiver, worn warm grey painted steel, fine sand in recesses, brass fasteners, black rubber buttstock pad, dark brown leather grip wrap, tiny restrained cyan cell. Matte, no baked light, no logos or text.','target_formats':['glb'],'alpha_thumbnail':True}
   r=api('POST',payload=options);m['tasks']['refine']=r['result'];m['refine_options']=options;save()
  print('Refine task:',m['tasks']['refine'],flush=True)

if __name__=='__main__':
 main()

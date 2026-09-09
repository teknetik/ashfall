"""Retain official CC0 PBR sources for the Ward building repair family."""
import concurrent.futures, hashlib, json, pathlib, urllib.request

ROOT=pathlib.Path('/home/teknetik/code/ao2')
OUT=ROOT/'refs/quality_20260909/building-materials'
ASSETS=['beige_wall_001','rock_surface','rough_concrete','rusty_metal_sheet']

def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'WardAssetProduction/1.0 (local game art authoring)'})
    with urllib.request.urlopen(request,timeout=60) as response:return response.read()

def acquire(asset):
    folder=OUT/asset;folder.mkdir(parents=True,exist_ok=True)
    metadata={}
    for endpoint in ['info','files']:
        path=folder/(endpoint+'.json')
        if not path.exists():path.write_bytes(get('https://api.polyhaven.com/'+endpoint+'/'+asset))
        metadata[endpoint]=json.loads(path.read_text())
    maps=[]
    for key in ['Diffuse','nor_gl','Rough','Displacement','Metal']:
        if key not in metadata['files']:continue
        row=metadata['files'][key]['4k']['png'];url=row['url']
        assert url.startswith('https://dl.polyhaven.org/')
        path=folder/url.rsplit('/',1)[-1]
        if not path.exists():path.write_bytes(get(url))
        blob=path.read_bytes();assert hashlib.md5(blob).hexdigest()==row['md5'],str(path)
        maps.append(dict(map=key,file=path.name,url=url,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),sourceMd5=row['md5']))
    record=dict(asset=asset,source='https://polyhaven.com/a/'+asset,license='CC0',licenseUrl='https://polyhaven.com/license',authors=metadata['info'].get('authors'),dimensionsMillimetres=metadata['info'].get('dimensions'),resolution='4k',maps=maps,status='Original retained PBR source; material assignment and native visual acceptance pending')
    (folder/'download-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:records=list(pool.map(acquire,ASSETS))
    (OUT/'download-manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([{'asset':r['asset'],'maps':len(r['maps']),'bytes':sum(x['bytes'] for x in r['maps'])} for r in records],indent=2))

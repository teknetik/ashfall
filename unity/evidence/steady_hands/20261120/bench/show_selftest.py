import json,sys
d=json.load(open(__file__.replace('show_selftest.py','selftest.json')))
print('pass',d['pass'],'failed',d['failed'])
for s in d['scenarios']:
    print('--',s['name'],s['ok'],s.get('frames'),s.get('actions'),s.get('result'))
    if not s['ok']: print('   ERR',s['error'][:700])
    for l in (s.get('log') or [])[-int(sys.argv[1]) if len(sys.argv)>1 else -5:]: print('     ',l[:230])

"""Run with python -m unittest discover -s unity/tools/devui -p 'test_*.py'."""
import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

from model import seed, validate, diagnostics
from server import App, BODY_MAX, draft_bytes


class ModelTests(unittest.TestCase):
    def test_seed_and_graph(self):
        data = seed()
        self.assertEqual([], validate(data))
        graph = diagnostics(data)
        self.assertIn('cracked_ceramic_bearing', graph['orphans'])
        self.assertEqual([], graph['impossible'])
        self.assertEqual([], graph['circular'])
    def test_broken_references_and_cycles(self):
        data=seed()
        data['recipes'][0]['inputs'][0]['ref']='missing:tag'
        self.assertTrue(any('impossible tag' in e for e in validate(data)))
        data=seed(); data['recipes'][0]['inputs'].append({'kind':'item','ref':'grip_stabilised_pistol','quantity':1})
        self.assertIn('grip_stabilised_pistol', diagnostics(data)['circular'])
        self.assertIn('grip_stabilised_pistol', diagnostics(data)['impossible'])
    def test_bad_and_duplicate_id(self):
        data=seed(); data['items'].append(dict(data['items'][0])); self.assertTrue(any('duplicate' in e for e in validate(data)))
        data['items'][-1]['id']='../../file'; self.assertTrue(any('invalid stable ID' in e for e in validate(data)))
    def test_loot_bounds_and_bool(self):
        data=seed();data['enemies'][0]['loot'][0]['chance']=101
        data['enemies'][0]['loot'][0]['min']=True
        self.assertGreaterEqual(len(validate(data)),2)


class ServerTests(unittest.TestCase):
    def test_unity_editor_export_is_separate_from_drafts(self):
        code, response = self.call('GET', '/api/unity-crafting')
        self.assertEqual(200, code)
        self.assertEqual('unity-editor-export', response['source'])
        data = response['data']
        self.assertEqual('ward-crafting/1', data['schema'])
        draft = seed()
        for kind in ('items', 'recipes', 'enemies'):
            self.assertTrue({x['id'] for x in draft[kind]} & {x['id'] for x in data[kind]})
        self.assertIn('grip_stabilised_pistol', {x['id'] for x in data['items']})
        self.assertEqual('weapon_scrap_pistol', data['weapons'][0]['id'])
        self.assertEqual('loot_feral_worker_droid', next(x for x in data['enemies'] if x['id'] == 'feral_worker_droid')['lootTableId'])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path.home())
        root=Path(self.tmp.name)
        self.app=App(0,root/'qa',root/'draft')
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()
        self.port=self.app.server_port
    def tearDown(self):
        self.app.shutdown();self.app.server_close();self.thread.join();self.tmp.cleanup()
    def call(self, method, path, body=None, headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.port,timeout=15)
        h={'Host':f'127.0.0.1:{self.port}',**(headers or {})}
        con.request(method,path,body=body,headers=h)
        response=con.getresponse();result=(response.status,json.loads(response.read()) if response.getheader('Content-Type','').startswith('application/json') else None);con.close();return result
    def restart(self):
        self.app.shutdown();self.app.server_close();self.thread.join()
        root=Path(self.tmp.name)
        self.app=App(0,root/'qa',root/'draft')
        self.thread=threading.Thread(target=self.app.serve_forever,daemon=True);self.thread.start()
        self.port=self.app.server_port
    def post_draft(self, revision, data):
        headers={'X-Ward-CSRF':self.app.token,'Content-Type':'application/json'}
        return self.call('POST','/api/import',json.dumps({'revision':revision,'data':data}),headers)
    def chain(self):
        items=[dict(id=f'i{i}',name='I',category='',subtype='',tier=1,
                    rarity='',weightKg=0,stack=1,tags=[],stats={}) for i in range(1000)]
        recipes=[dict(id=f'r{i}',name='R',station='s0',seconds=1,
                      inputs=[dict(kind='item',ref=items[i]['id'],quantity=1)],
                      outputs=[dict(itemId=items[i+1]['id'],quantity=1)]) for i in range(999)]
        return dict(schemaVersion=1,source='draft',items=items,recipes=recipes,enemies=[])
    def test_preflight_serialized_limit_preserves_draft_after_restart(self):
        before=self.call('GET','/api/draft')[1]
        data=self.chain()
        for item in data['items']: item['name']='N'*120
        wire=json.dumps({'revision':before['revision'],'data':data}).encode()
        self.assertLess(len(wire),BODY_MAX)
        self.assertGreater(len(draft_bytes(data)),BODY_MAX)
        code,_=self.post_draft(before['revision'],data)
        self.assertEqual(413,code)
        self.assertEqual(before['revision'],self.call('GET','/api/draft')[1]['revision'])
        self.restart()
        self.assertEqual(before['revision'],self.call('GET','/api/draft')[1]['revision'])
    def test_deep_chain_diagnostics_and_restart(self):
        before=self.call('GET','/api/draft')[1]
        data=self.chain()
        self.assertEqual([],validate(data))
        self.assertLessEqual(len(draft_bytes(data)),BODY_MAX)
        code,result=self.post_draft(before['revision'],data)
        self.assertEqual(200,code)
        self.assertEqual(999,len(result['diagnostics']['edges']))
        self.assertEqual(result['revision'],self.call('GET','/api/draft')[1]['revision'])
        self.restart()
        self.assertEqual(result['revision'],self.call('GET','/api/draft')[1]['revision'])
    def test_expanded_graph_cap_rejects_before_persist(self):
        before=self.call('GET','/api/draft')[1]
        data=self.chain()
        for item in data['items']: item['tags']=['shared']
        data['recipes']=data['recipes'][:22]
        for recipe in data['recipes']:
            recipe['inputs']=[dict(kind='tag',ref='shared',quantity=1)]
        self.assertEqual([],validate(data))
        self.assertLessEqual(len(draft_bytes(data)),BODY_MAX)
        self.assertEqual(400,self.post_draft(before['revision'],data)[0])
        self.assertEqual(before['revision'],self.call('GET','/api/draft')[1]['revision'])
    def test_draft_symlink_swap_and_directory_reparent(self):
        before=self.call('GET','/api/draft')[1]
        path=self.app.draft_file
        original=path.read_bytes()
        other=Path(self.tmp.name)/'other.json'
        other.write_bytes(original)
        path.unlink();path.symlink_to(other)
        self.assertEqual(409,self.call('GET','/api/draft')[0])
        self.assertEqual(409,self.post_draft(before['revision'],before['data'])[0])
        self.assertEqual(original,other.read_bytes())
        path.unlink();path.write_bytes(original)
        folder=path.parent
        moved=folder.with_name('moved')
        folder.rename(moved)
        folder.symlink_to(moved,target_is_directory=True)
        self.assertEqual(409,self.call('GET','/api/draft')[0])
        self.assertEqual(409,self.post_draft(before['revision'],before['data'])[0])
        folder.unlink();moved.rename(folder)
        self.assertEqual(before['revision'],self.call('GET','/api/draft')[1]['revision'])
    def test_absent_and_defences(self):
        self.assertEqual('absent',self.call('GET','/api/status')[1]['status'])
        payload=json.dumps({'action':'dev.item.grant','itemId':'scrap_coil','quantity':1})
        self.assertEqual(403,self.call('POST','/api/command',payload)[0])
        headers={'X-Ward-CSRF':self.app.token,'Content-Type':'application/json'}
        self.assertEqual(503,self.call('POST','/api/command',payload,headers)[0]);self.assertFalse((self.app.qa/'command.json').exists())
        self.assertEqual(403,self.call('POST','/api/command',payload,{**headers,'Origin':'http://evil.test'})[0])
        self.assertEqual(403,self.call('GET','/api/status',headers={'Host':f'evil.test:{self.port}'})[0])
        self.assertEqual(413,self.call('POST','/api/command',' '*8193,headers)[0])
        self.assertEqual(400,self.call('POST','/api/command','{bad',headers)[0])
        self.assertEqual(400,self.call('POST','/api/command',json.dumps({'action':'quit'}),headers)[0])
    def test_draft_save_conflict_import_and_validation(self):
        r=self.call('GET','/api/draft')[1]
        self.assertEqual('draft',r['source'])
        data=r['data'];data['items'][0]['name']='Adjusted'
        headers={'X-Ward-CSRF':self.app.token,'Content-Type':'application/json'}
        payload=json.dumps({'revision':r['revision'],'data':data})
        self.assertEqual(200,self.call('POST','/api/draft',payload,headers)[0])
        self.assertEqual(409,self.call('POST','/api/draft',payload,headers)[0])
        now=self.call('GET','/api/draft')[1]
        data=now['data'];data['items'][0]['id']='../../etc/passwd'
        self.assertEqual(400,self.call('POST','/api/import',json.dumps({'revision':now['revision'],'data':data}),headers)[0])
        self.assertEqual('Adjusted',self.call('GET','/api/draft')[1]['data']['items'][0]['name'])
    def test_symlink_qa_path(self):
        root=Path(self.tmp.name)
        (root/'bad').symlink_to(root/'qa',target_is_directory=True)
        with self.assertRaises(ValueError): App(0,root/'bad',root/'draft2')
        with self.assertRaises(ValueError): App(0,root/'qa'/'..'/'qa',root/'draft2')
    def test_malformed_import_and_nonfinite_rejected(self):
        r=self.call('GET','/api/draft')[1]
        data=r['data'];data['recipes'][0]['inputs'][0]['ref']=[]
        h={'X-Ward-CSRF':self.app.token,'Content-Type':'application/json'}
        self.assertEqual(400,self.call('POST','/api/import',json.dumps({'revision':r['revision'],'data':data}),h)[0])
        data=seed();data['items'][0]['weightKg']=float('nan')
        self.assertEqual(400,self.call('POST','/api/draft',json.dumps({'revision':r['revision'],'data':data}),h)[0])
        self.assertEqual(r['revision'],self.call('GET','/api/draft')[1]['revision'])
    def test_fake_protocol_state_is_test_only(self):
        # A test fixture exercises protocol mechanics; it is NEVER served by production startup.
        state={'schemaVersion':1,'source':'unity','available':True,
               'build':{'development':True},'items':[{'id':'scrap_coil'}],
               'encounters':[{'key':'Machine depot nest'}]}
        state_path=self.app.qa/'dev-state.json'
        state_path.write_text(json.dumps(state))
        h={'X-Ward-CSRF':self.app.token,'Content-Type':'application/json'}
        self.assertEqual('connected',self.call('GET','/api/status')[1]['status'])
        self.assertEqual(400,self.call('POST','/api/command',json.dumps({'action':'dev.item.grant','itemId':'droid_servo_damaged','quantity':1}),h)[0])
        self.assertFalse((self.app.qa/'command.json').exists())
        def acknowledge():
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                path=self.app.qa/'command.json'
                if path.exists():
                    cmd=json.loads(path.read_text());path.unlink()
                    (self.app.qa/'ack.json').write_text(json.dumps({'id':cmd['id'],'success':True}))
                    return
                time.sleep(.01)
            self.fail('Command never reached bridge slot')
        t=threading.Thread(target=acknowledge);t.start()
        code,body=self.call('POST','/api/command',json.dumps({'action':'dev.item.grant','itemId':'scrap_coil','quantity':1}),h)
        t.join();self.assertEqual(200,code);self.assertTrue(body['ack']['success'])
        os.utime(state_path,(time.time()-10,time.time()-10))
        self.assertEqual('stale',self.call('GET','/api/status')[1]['status'])
        self.assertEqual(503,self.call('POST','/api/command',json.dumps({'action':'dev.state'}),h)[0])
        self.assertFalse((self.app.qa/'command.json').exists())

if __name__=='__main__': unittest.main()

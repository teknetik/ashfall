"""Authoring contract/security tests use fake transports; no paid API calls."""
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import wave

from ai_authoring import AuthoringJobs, AuthoringError, load_credential, request_openai, read_regular
from model import seed, validate
from server import App


KEY = 'test-only-credential-never-returned'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jWQAAAABJRU5ErkJggg==')
COPY = {'name': 'Rebuilt servo', 'description': 'A repaired actuator with a sand-scored casing.', 'designNotes': 'Existing stats are unchanged.'}


def text_response(value=COPY):
    text = json.dumps(value) if isinstance(value, dict) else value
    return json.dumps({'id': 'resp_test', 'status': 'completed', 'output': [
        {'type': 'reasoning', 'summary': []}, {'type': 'message', 'content': [
            {'type': 'output_text', 'text': text}]}], 'usage': {'input_tokens': 10, 'output_tokens': 20}}).encode(), 'req_test'


def wait_job(manager, ident):
    deadline = time.monotonic() + 5
    while manager.active and time.monotonic() < deadline: time.sleep(.01)
    assert manager.active is None, 'worker did not finish'
    return next(x for x in manager.list() if x['id'] == ident)


class AuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.home())
        self.root = Path(self.temp.name)
        (self.root / 'media').mkdir()
        (self.root / '.env').write_text('OPENAI_API_KEY=' + KEY)
        (self.root / 'lore.md').write_text('Ward is on Tir. Its isolation remains unknown.')
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start()
        self.calls = []
        def transport(endpoint, payload, key):
            self.calls.append((endpoint, payload, key))
            return text_response()
        self.manager = AuthoringJobs(self.root, self.root / 'media', transport=transport)
    def tearDown(self):
        self.env.stop(); self.temp.cleanup()
    def start_copy(self):
        return self.manager.start({'kind': 'item_text', 'prompt': 'Practical mechanical salvage.', 'item': seed()['items'][1]})
    def test_key_discovery_is_not_execution_and_does_not_surface_secret(self):
        (self.root / '.env').write_text('# Settings\nexport OPENAI_API_KEY="' + KEY + '" # local only\n')
        self.assertEqual(KEY, load_credential(self.root)[0])
        self.assertNotIn(KEY, json.dumps(self.manager.config()))
        self.assertTrue(self.manager.config()['configured'])
        (self.root / '.env').unlink(); (self.root / '.env').symlink_to(self.root / 'lore.md')
        self.assertIsNone(load_credential(self.root)[0])
    def test_git_worktree_root_fallback(self):
        primary = self.root / 'primary'; primary.mkdir()
        git = primary / '.git'; (git / 'worktrees' / 'feature').mkdir(parents=True)
        (git / 'worktrees' / 'feature' / 'commondir').write_text('../..')
        worktree = self.root / 'worktree'; worktree.mkdir()
        (worktree / '.git').write_text('gitdir: ' + str(git / 'worktrees' / 'feature'))
        (primary / '.env').write_text('OPENAI_API_KEY=' + KEY)
        self.assertEqual(KEY, load_credential(worktree)[0])
    def test_copy_is_reviewable_persistent_and_never_mutates_item(self):
        item = seed()['items'][1]; original = json.dumps(item, sort_keys=True)
        job = self.manager.start({'kind': 'item_text', 'prompt': 'Suggest copy', 'item': item})
        result = wait_job(self.manager, job['id'])
        self.assertEqual('complete', result['status'])
        self.assertEqual(COPY, result['result'])
        self.assertEqual(original, json.dumps(item, sort_keys=True))
        self.assertEqual('responses', self.calls[0][0])
        payload = self.calls[0][1]
        self.assertFalse(payload['store'])
        self.assertEqual('json_schema', payload['text']['format']['type'])
        self.assertNotIn(KEY, json.dumps(result))
        self.assertNotIn(KEY.encode(), (self.root / 'media' / (job['id']+'.json')).read_bytes())
        reloaded = AuthoringJobs(self.root, self.root / 'media')
        self.assertEqual(COPY, reloaded.list()[0]['result'])
    def test_no_key_and_unknown_operation_never_start_request(self):
        (self.root / '.env').unlink()
        with self.assertRaises(AuthoringError): self.start_copy()
        with self.assertRaises(AuthoringError): self.manager.start({'kind': 'exec', 'prompt': 'test'})
        self.assertEqual([], self.calls)
    def test_cancel_discards_result_and_does_not_queue_another_paid_request(self):
        running = threading.Event(); release = threading.Event()
        def transport(*args): running.set(); release.wait(3); return text_response()
        self.manager.transport = transport
        job = self.start_copy(); self.assertTrue(running.wait(2))
        self.assertEqual('cancelled', self.manager.cancel(job['id'])['status'])
        with self.assertRaises(AuthoringError): self.start_copy()
        release.set(); result = wait_job(self.manager, job['id'])
        self.assertEqual('cancelled', result['status']); self.assertIsNone(result['result'])
    def test_refusal_incomplete_and_malformed_outputs_are_not_applied(self):
        responses = [({'status': 'incomplete', 'output': []}),
                     ({'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'No'}]}]}),
                     ({'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{bad'}]}]})]
        for response in responses:
            self.manager.transport = lambda *args: (json.dumps(response).encode(), 'req_test')
            result = wait_job(self.manager, self.start_copy()['id'])
            self.assertEqual('failed', result['status']); self.assertIsNone(result['result'])
    def test_provider_error_text_never_leaks_key(self):
        def fail(*args): raise RuntimeError(KEY + ' unexpected provider error')
        self.manager.transport = fail
        result = wait_job(self.manager, self.start_copy()['id'])
        self.assertEqual('failed', result['status']); self.assertNotIn(KEY, json.dumps(result))
        class FailOpener:
            def open(self, *args, **kwargs):
                raise HTTPError('https://api.openai.com', 401, KEY, {}, BytesIO(KEY.encode()))
        with patch('ai_authoring.build_opener', return_value=FailOpener()):
            with self.assertRaises(AuthoringError) as error: request_openai('responses', {}, KEY)
            self.assertNotIn(KEY, str(error.exception))
    def test_image_and_voice_store_original_bytes_with_hash_and_provenance(self):
        self.manager.transport = lambda *args: (json.dumps({'data': [{'b64_json': base64.b64encode(PNG).decode()}]}).encode(), 'req_img')
        job = self.manager.start({'kind': 'icon', 'prompt': 'A servo', 'item': seed()['items'][1]})
        result = wait_job(self.manager, job['id'])
        self.assertEqual('complete', result['status']); self.assertEqual(PNG, self.manager.media(job['id'], 'png'))
        self.assertEqual(64, len(result['asset']['sha256']))
        stream = BytesIO()
        with wave.open(stream, 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(24000); output.writeframes(b'\0\0' * 24)
        wav = stream.getvalue()
        self.manager.transport = lambda *args: (wav, 'req_voice')
        job = self.manager.start({'kind': 'voice', 'prompt': 'Mira audition', 'speech': 'Water before the road.', 'voice': 'cedar', 'direction': 'Warm'})
        result = wait_job(self.manager, job['id'])
        self.assertEqual('complete', result['status']); self.assertEqual(wav, self.manager.media(job['id'], 'wav'))
        self.assertIn('AI-generated', result['disclosure'])
    def test_media_traversal_symlink_and_directory_swaps_refused(self):
        with self.assertRaises(AuthoringError): self.manager.media('../secret', 'png')
        with self.assertRaises(AuthoringError): self.manager.media('f'*32, 'svg')
        ident='f'*32; (self.root / 'media' / (ident+'.png')).symlink_to(self.root / '.env')
        with self.assertRaises(OSError): self.manager.media(ident, 'png')
        (self.root / 'media').rename(self.root / 'original')
        (self.root / 'media').symlink_to(self.root / 'original', target_is_directory=True)
        with self.assertRaises(OSError): self.manager.media(ident, 'png')
    def test_equipment_schema_enforces_three_implant_sockets_and_component_compatibility(self):
        data=seed(); item=data['items'][0]
        item['equipment']={'kind':'implant','slots':['implant_legs'],'socketTypes':[],
            'modificationSockets':[{'id':'augmentation_'+str(i),'label':'Augmentation '+str(i),'type':'implant'} for i in (1,2,3)],
            'modifiers':[{'stat':'movementSpeed','flat':0,'percent':.08}]}
        self.assertEqual([],validate(data))
        item['equipment']['modificationSockets'].pop()
        self.assertTrue(any('exactly three' in error for error in validate(data)))
        item['equipment'].update(kind='armour_mod',slots=[],socketTypes=[],modificationSockets=[])
        self.assertTrue(any('compatible socket type' in error for error in validate(data)))
        item['equipment']['socketTypes']=['armour_motor']
        self.assertEqual([],validate(data))

    def test_storage_failure_does_not_hold_paid_request_slot(self):
        with patch('ai_authoring.atomic_media',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):self.start_copy()
        self.assertIsNone(self.manager.active)
        self.assertEqual([],self.calls)

    def test_v1_drafts_accept_only_bounded_new_copy_and_local_media(self):
        value = seed(); value['items'][0].update(description='A repaired weapon.', designNotes='Draft only.', buyPrice=100, sellPrice=25, iconAsset='/api/ai/assets/'+'f'*32+'.png', aiProvenance=['f'*32])
        self.assertEqual([], validate(value))
        value['items'][0]['iconAsset']='https://arbitrary.example/icon.png'
        self.assertTrue(any('iconAsset' in error for error in validate(value)))
        value['items'][0]['description']='x'*1201
        self.assertTrue(any('description' in error for error in validate(value)))


if __name__ == '__main__': unittest.main()

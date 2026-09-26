"""Fake-file transport regression tests; no Unity process or desktop input."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("tree_shadow_runner",Path(__file__).with_name("runner.py"))
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=Path(self.temp.name)
        self.receipts=self.folder/"receipts"
        self.receipts.mkdir()
        self.client=runner.NativeClient(self.folder,os.getpid(),self.receipts,timeout=.15)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def consume(self, behavior):
        for _ in range(100):
            if (self.folder/"command.json").exists():
                command=json.loads((self.folder/"command.json").read_text())
                (self.folder/"command.json").unlink()
                behavior(command)
                return
            await asyncio.sleep(.002)
        self.fail("Client did not send a command")

    def ack(self, command, **extra):
        value=dict(id=command["id"],success=True)
        value.update(extra)
        (self.folder/"ack.json").write_text(json.dumps(value))

    async def roundtrip(self, behavior, action="view"):
        consumer=asyncio.create_task(self.consume(behavior))
        try:
            return await self.client.command({"action":action})
        finally:
            await consumer

    async def test_matching_success_with_fresh_response_is_accepted(self):
        def respond(command):
            (self.folder/"settings.json").write_text('{"renderScale":1}')
            self.ack(command)
        result=await self.roundtrip(respond,"settingsSnapshot")
        self.assertEqual(result,{"renderScale":1})
        receipt=json.loads(next(self.receipts.iterdir()).read_text())
        self.assertTrue(receipt["accepted"])

    async def test_stale_ack_never_counts_as_success(self):
        (self.folder/"ack.json").write_text('{"id":"previous-command","success":true}')
        with self.assertRaisesRegex(TimeoutError,"stale ack was not accepted"):
            await self.roundtrip(lambda command:None)

    async def test_explicit_failed_matching_ack_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Matching acknowledgement explicitly failed"):
            await self.roundtrip(lambda command:self.ack(command,success=False))

    async def test_malformed_ack_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Cannot read valid JSON"):
            await self.roundtrip(lambda command:(self.folder/"ack.json").write_text('{broken'))

    async def test_wrong_ack_schema_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Malformed acknowledgement"):
            await self.roundtrip(lambda command:self.ack(command,success="true"))

    async def test_unexpected_ack_id_detects_competing_writer(self):
        with self.assertRaisesRegex(RuntimeError,"Unexpected acknowledgement ID"):
            await self.roundtrip(lambda command:self.ack(command,id="somebody-else"))
        self.assertTrue(self.client.competing_writer)

    async def test_changed_ack_between_commands_detects_lost_ownership(self):
        await self.roundtrip(self.ack)
        (self.folder/"ack.json").write_text('{"id":"other-writer-after-our-ack","success":true}')
        with self.assertRaisesRegex(RuntimeError,"command ownership was lost"):
            await self.client.command({"action":"view"})
        self.assertTrue(self.client.competing_writer)

    async def test_native_error_file_is_preserved_and_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"Native command error"):
            await self.roundtrip(lambda command:(self.folder/"qa-error.json").write_text('{"error":"simulated"}'))
        self.assertEqual(json.loads((self.folder/"qa-error.json").read_text()),{"error":"simulated"})

    async def test_ack_does_not_validate_stale_response_file(self):
        (self.folder/"settings.json").write_text('{"old":true}')
        with self.assertRaisesRegex(RuntimeError,"missing/stale response"):
            await self.roundtrip(self.ack,"settingsSnapshot")

    async def test_existing_command_is_not_overwritten(self):
        (self.folder/"command.json").write_text('{"id":"owned-by-another-run"}')
        with self.assertRaisesRegex(RuntimeError,"Unconsumed command"):
            await self.client.command({"action":"view"})
        self.assertEqual(json.loads((self.folder/"command.json").read_text())["id"],"owned-by-another-run")

    def test_existing_evidence_file_is_not_reused(self):
        target=self.folder/"evidence.json"
        runner.write_new(target,{"first":True})
        with self.assertRaises(FileExistsError):
            runner.write_new(target,{"first":False})
        self.assertEqual(json.loads(target.read_text()),{"first":True})


if __name__=="__main__":
    unittest.main(verbosity=2)

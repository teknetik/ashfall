"""Offline only: mocks, synthetic PNGs and harmless Python subprocesses; no Unity/X11."""
import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import ANY, AsyncMock, Mock, patch

os.environ.setdefault('ATHEN_NATIVE_DIR', '/nonexistent-offline-test')
import capture_basic_general_sign as capture
import launch_phase1_qa as launcher
from PIL import Image

TOOLS = Path(__file__).resolve().parent
SNAPSHOT = dict(frame=1, width=1920, height=1080, session={'state': 'Play'}, player={'position': [0, 0, 0]})


class CaptureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.patches = [patch.object(capture, 'OUT', self.out), patch.object(capture, 'snap', return_value=SNAPSHOT)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def report(self) -> dict:
        return dict(reportFile='report.json', captures=[], approachRoute={})

    def png(self, size=(1920, 1080)):
        buffer = io.BytesIO()
        Image.new('RGB', size, 'orange').save(buffer, format='PNG')
        return buffer.getvalue()

    async def test_unique_capture_names_and_stale_named_file_untouched(self):
        stale = self.out / 'oblique.png'
        stale.write_bytes(self.png())
        data = stale.read_bytes()

        async def command(j):
            (self.out / (j['name'] + '.png')).write_bytes(data)
        client = SimpleNamespace(command=command)
        first = await capture.shot(client, 'oblique', timeout=1)
        second = await capture.shot(client, 'oblique', timeout=1)
        self.assertNotEqual(first['path'], second['path'])
        self.assertNotEqual(first['path'], stale.name)
        self.assertEqual(stale.read_bytes(), data)

    async def test_stale_png_cannot_satisfy_missing_new_capture(self):
        (self.out / 'oblique.png').write_bytes(self.png())
        with self.assertRaises(TimeoutError):
            await capture.shot(SimpleNamespace(command=AsyncMock()), 'oblique', timeout=.02)

    async def test_partial_png_completes_before_deadline(self):
        data = self.png()
        tasks = []

        async def complete(path):
            await asyncio.sleep(.05)
            path.write_bytes(data)

        async def command(j):
            path = self.out / (j['name'] + '.png')
            path.write_bytes(data[:32])
            tasks.append(asyncio.create_task(complete(path)))
        record = await capture.shot(SimpleNamespace(command=command), 'partial', timeout=1)
        await asyncio.gather(*tasks)
        self.assertEqual((self.out / record['path']).read_bytes(), data)

    async def test_corrupt_complete_png_times_out(self):
        async def command(j):
            (self.out / (j['name'] + '.png')).write_bytes(b'broken' + b'\x00\x00\x00\x00IEND\xaeB`\x82')
        with self.assertRaises(TimeoutError):
            await capture.shot(SimpleNamespace(command=command), 'broken', timeout=.02)

    async def test_wrong_dimensions_fail(self):
        async def command(j):
            (self.out / (j['name'] + '.png')).write_bytes(self.png((32, 32)))
        with self.assertRaises(AssertionError):
            await capture.shot(SimpleNamespace(command=command), 'small', timeout=1)

    async def test_each_smoke_selects_only_one_oblique_and_one_noon_capture(self):
        for leg in ('left', 'right'):
            report = self.report()
            walks = []

            async def walk(c, d, report, name, pos):
                walks.append((name, pos))
                return {'position': pos}
            shot = AsyncMock(return_value={'path': 'synthetic.png'})
            with patch.object(capture, 'recorded_walk', side_effect=walk), patch.object(capture, 'aim', AsyncMock(return_value=(1, 2))), patch.object(capture, 'set_hour', AsyncMock()) as hour, patch.object(capture, 'shot', shot), patch.object(capture.asyncio, 'sleep', AsyncMock()):
                await capture.smoke(SimpleNamespace(command=AsyncMock()), None, report, leg)
            self.assertEqual(walks[:-2], capture.APPROACH)
            self.assertEqual([x[0] for x in walks[-2:]], ['lane_alignment', 'fp_sign_' + leg])
            shot.assert_awaited_once()
            hour.assert_awaited_once_with(ANY, 12.0)
            self.assertEqual(len(report['captures']), 1)

    async def test_failed_leg_persists_target_and_prior_success(self):
        report = self.report()
        report['approachRoute']['prior'] = {'reached': True}
        with patch.object(capture, 'walk_to', AsyncMock(side_effect=RuntimeError('BLOCKED'))):
            with self.assertRaisesRegex(RuntimeError, 'BLOCKED'):
                await capture.recorded_walk(None, None, report, 'oblique', (6.2, 0, 18.8))
        saved = json.loads((self.out / 'report.json').read_text())
        self.assertTrue(saved['approachRoute']['prior']['reached'])
        self.assertEqual(saved['currentLeg']['tolerance'], .3)
        self.assertEqual(saved['currentLeg']['seconds'], 70)

    async def test_walk_retains_contract_and_hard_timeout(self):
        report = self.report()
        walk = AsyncMock(return_value={'position': [1, 0, 1]})
        with patch.object(capture, 'walk_to', walk):
            await capture.recorded_walk(None, None, report, 'target', (1, 0, 1))
        walk.assert_awaited_once_with(None, None, (1, 0, 1), .3, 70)
        # Exercise the real inherited six-stall guard without keyboard or elapsed sleeps.
        module = sys.modules[capture.walk_to.__module__]
        with patch.object(module, 'snap', return_value=SNAPSHOT), patch.object(module, 'key'), patch.object(module.asyncio, 'sleep', AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, 'BLOCKED'):
                await module.walk_to(SimpleNamespace(command=AsyncMock()), None, (1, 0, 1), .3, 70)

    async def test_failure_before_focus_is_reported(self):
        with patch.dict(os.environ, ATHEN_NATIVE_PID='123'), patch.object(capture, 'focus_window', side_effect=RuntimeError('no focus')):
            with self.assertRaisesRegex(RuntimeError, 'no focus'):
                await capture.main(capture.parse_args(['smoke', '--leg', 'left']))
        report = json.loads(next(self.out.glob('basic-general-sign-*.json')).read_text())
        self.assertFalse(report['complete'])
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['error']['message'], 'no focus')

    async def test_incremental_report_survives_exception_or_cancellation(self):
        for error in (RuntimeError('route failure'), asyncio.CancelledError()):
            async def run(args, c, d, report):
                report['captures'].append({'path': 'synthetic-only.png'})
                capture.checkpoint(report)
                self.assertEqual(json.loads((self.out / report['reportFile']).read_text())['status'], 'running')
                raise error
            with patch.dict(os.environ, ATHEN_NATIVE_PID='123'), patch.object(capture, 'focus_window', return_value=(Mock(), SimpleNamespace(id=9))), patch.object(capture, 'snap', side_effect=[dict(SNAPSHOT, frame=1), dict(SNAPSHOT, frame=2), SNAPSHOT]), patch.object(capture, 'key'), patch.object(capture, 'run', side_effect=run):
                with self.assertRaises(type(error)):
                    await capture.main(capture.parse_args(['smoke', '--leg', 'left']))
        reports = [json.loads(p.read_text()) for p in self.out.glob('basic-general-sign-*.json')]
        self.assertEqual(len(reports), 2)
        for report in reports:
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(len(report['captures']), 1)

    async def test_success_report(self):
        with patch.dict(os.environ, ATHEN_NATIVE_PID='123'), patch.object(capture, 'focus_window', return_value=(Mock(), SimpleNamespace(id=9))), patch.object(capture, 'snap', side_effect=[dict(SNAPSHOT, frame=1), dict(SNAPSHOT, frame=2)]), patch.object(capture, 'key'), patch.object(capture, 'run', AsyncMock()):
            await capture.main(capture.parse_args(['smoke', '--leg', 'right']))
        report = json.loads(next(self.out.glob('basic-general-sign-*.json')).read_text())
        self.assertTrue(report['complete'])
        self.assertEqual(report['status'], 'passed')

    async def test_focus_loss_never_sends_command(self):
        report = self.report()
        display = Mock()
        display.get_input_focus.return_value.focus.id = 999
        with patch.object(capture.Client, 'command', AsyncMock()) as send:
            client = capture.ReportingClient(report, display, SimpleNamespace(id=123))
            with self.assertRaisesRegex(RuntimeError, 'lost keyboard focus'):
                await client.command({'action': 'reset'})
            send.assert_not_awaited()
        self.assertEqual(json.loads((self.out / 'report.json').read_text())['focusWindow'], 999)

    async def test_stale_bridge_is_reported_without_running_route(self):
        with patch.dict(os.environ, ATHEN_NATIVE_PID='123'), patch.object(capture, 'focus_window', return_value=(Mock(), SimpleNamespace(id=9))), patch.object(capture, 'key'), patch.object(capture.asyncio, 'sleep', AsyncMock()), patch.object(capture, 'run', AsyncMock()) as run:
            with self.assertRaisesRegex(TimeoutError, 'not advancing'):
                await capture.main(capture.parse_args(['smoke', '--leg', 'left']))
            run.assert_not_awaited()
        report = json.loads(next(self.out.glob('basic-general-sign-*.json')).read_text())
        self.assertEqual(report['status'], 'failed')

    async def test_success_cannot_hide_input_cleanup_error(self):
        with patch.dict(os.environ, ATHEN_NATIVE_PID='123'), patch.object(capture, 'focus_window', return_value=(Mock(), SimpleNamespace(id=9))), patch.object(capture, 'snap', side_effect=[dict(SNAPSHOT, frame=1), dict(SNAPSHOT, frame=2)]), patch.object(capture, 'key', side_effect=RuntimeError('input disconnected')), patch.object(capture, 'run', AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, 'Input cleanup failed'):
                await capture.main(capture.parse_args(['smoke', '--leg', 'right']))
        report = json.loads(next(self.out.glob('basic-general-sign-*.json')).read_text())
        self.assertFalse(report['complete'])
        self.assertEqual(report['status'], 'failed')


class CliTests(unittest.TestCase):
    def test_no_stage_or_invalid_selection_exits_two(self):
        for argv in ([], ['typo'], ['smoke'], ['smoke', '--leg', 'porch'], ['mem', '--leg', 'left'], ['all']):
            with self.subTest(argv=argv):
                result = subprocess.run([sys.executable, str(TOOLS / 'capture_basic_general_sign.py'), *argv], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_wrapper_propagates_exact_exit_without_launching(self):
        with tempfile.TemporaryDirectory() as folder:
            uv = Path(folder) / 'uv'
            uv.write_text('#!/bin/sh\nexit 37\n')
            uv.chmod(0o755)
            env = dict(os.environ, PATH=folder + os.pathsep + os.environ['PATH'])
            result = subprocess.run(['bash', str(TOOLS / 'relaunch_qa.sh'), '/unused', 'left'], env=env, timeout=5)
            self.assertEqual(result.returncode, 37)
            for args in ([], ['/unused'], ['/unused', 'all']):
                result = subprocess.run(['bash', str(TOOLS / 'relaunch_qa.sh'), *args], env=env, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 2)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        settings = self.root / 'unity/evidence/courtyard/20260908/after-native/settings.json'
        settings.parent.mkdir(parents=True)
        settings.write_text('{"video": {}}')
        patcher = patch.object(launcher, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self):
        return SimpleNamespace(evidence=self.root / 'new-run', display=':fake', capped=False, background=False, smoke_leg='left')

    def player(self, code):
        # Only harmless Python child processes are created by this test suite.
        p = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(launcher.stop_owned, p)
        return p

    def test_startup_exit_status_and_signal_are_retained(self):
        for source, expected, raw in [('import sys; sys.exit(23)', 23, 23), ('import os,signal; os.kill(os.getpid(),signal.SIGTERM)', 143, -15), ('pass', 1, 0)]:
            args = self.args()
            args.evidence = self.root / ('run-' + str(expected))
            player = self.player(source)
            player.wait(timeout=5)
            with patch.object(launcher.subprocess, 'Popen', return_value=player) as popen:
                self.assertEqual(launcher.launch(args), expected)
            popen.assert_called_once()
            report = json.loads((args.evidence / 'launch-report.json').read_text())
            self.assertEqual(report['playerReturncode'], raw)
            self.assertFalse(report['complete'])

    def test_success_and_capture_failure_cleanup_only_owned_pid(self):
        unrelated = self.player('import time; time.sleep(60)')
        for status in (0, 17):
            args = self.args()
            args.evidence = self.root / ('capture-' + str(status))
            player = self.player('import time; time.sleep(60)')
            window = self.player('pass')
            capture_child = self.player('import sys; sys.exit(%d)' % status)
            window.wait(timeout=5)
            capture_child.wait(timeout=5)
            with patch.object(launcher.subprocess, 'Popen', side_effect=[player, window, capture_child]) as popen, patch.object(launcher, 'wait_bridge'):
                self.assertEqual(launcher.launch(args), status)
            self.assertEqual(popen.call_count, 3)
            report = json.loads((args.evidence / 'launch-report.json').read_text())
            self.assertEqual(report['captureReturncode'], status)
            self.assertEqual(report['complete'], status == 0)
            self.assertTrue(report['playerStopRequested'])
            self.assertEqual(player.returncode, -signal.SIGTERM)
            self.assertIsNone(unrelated.poll())

    def test_startup_timeout_is_reported_and_owned_player_stopped(self):
        args = self.args()
        player = self.player('import time; time.sleep(60)')
        with patch.object(launcher.subprocess, 'Popen', return_value=player), patch.object(launcher, 'wait_bridge', side_effect=TimeoutError('synthetic startup deadline')):
            self.assertEqual(launcher.launch(args), 124)
        report = json.loads((args.evidence / 'launch-report.json').read_text())
        self.assertFalse(report['complete'])
        self.assertEqual(player.returncode, -signal.SIGTERM)

    def test_existing_directory_refused_without_launch_or_rotation(self):
        args = self.args()
        args.evidence.mkdir()
        (args.evidence / 'snapshot.json').write_text('preserve')
        with patch.object(launcher.subprocess, 'Popen') as popen:
            with self.assertRaises(FileExistsError):
                launcher.launch(args)
            popen.assert_not_called()
        self.assertEqual((args.evidence / 'snapshot.json').read_text(), 'preserve')

    def test_helper_timeout_and_player_exit_are_bounded(self):
        player = self.player('import time; time.sleep(60)')
        child = self.player('import time; time.sleep(60)')
        with self.assertRaises(TimeoutError):
            launcher.wait_child(player, child, .01)
        launcher.stop_owned(player)
        with self.assertRaises(launcher.PlayerExited):
            launcher.wait_child(player, child, 1)
        with self.assertRaises(TimeoutError):
            launcher.wait_bridge(child, self.root, .01)


if __name__ == '__main__':
    # Suppress routine JSON reports while keeping unittest results/tracebacks.
    with contextlib.redirect_stdout(io.StringIO()):
        unittest.main(verbosity=2)

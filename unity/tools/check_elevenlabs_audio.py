"""Native audio acceptance: record only this player's PulseAudio sink.

uv run --with python-xlib python unity/tools/check_elevenlabs_audio.py
"""
import asyncio
import array
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/audio/20260908/native'


def command(*args):
    return subprocess.check_output(args, text=True).strip()


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ('snapshot.json', 'command.json', 'ack.json', 'qa-error.json'):
        (OUT / name).unlink(missing_ok=True)
    report = {'complete': False, 'recordings': []}
    process = None
    sink = 'athen_audio_' + str(os.getpid())
    module = command('pactl', 'load-module', 'module-null-sink', 'sink_name=' + sink,
        'sink_properties=device.description=AthenAudioQA')
    recording = None
    try:
        env = dict(os.environ, PULSE_SINK=sink)
        process = subprocess.Popen([str(ROOT / 'AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'),
            '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
            '-logFile', str(OUT / 'Player.log'), '--athen-qa', str(OUT)], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ.update(ATHEN_NATIVE_DIR=str(OUT), ATHEN_NATIVE_PID=str(process.pid), ATHEN_EVIDENCE=str(OUT))
        from desktop_input import focus, key
        from native_client import Client
        deadline = time.monotonic() + 60
        while not (OUT / 'snapshot.json').exists():
            if process.poll() is not None: raise RuntimeError('Player exited during launch')
            if time.monotonic() > deadline: raise TimeoutError('No native snapshot')
            await asyncio.sleep(.2)
        d = focus()

        def snapshot(): return json.loads((OUT / 'snapshot.json').read_text())

        async def route_player_audio():
            # Unity/FMOD may select an enumerated device and ignore PULSE_SINK.
            # Move only this test player's stream, never another application's.
            for _ in range(30):
                streams = json.loads(command('pactl', '-f', 'json', 'list', 'sink-inputs'))
                owned = [s for s in streams if str(s['properties'].get('application.process.id')) == str(process.pid)]
                if owned:
                    for stream in owned:
                        command('pactl', 'move-sink-input', str(stream['index']), sink)
                    return
                await asyncio.sleep(.2)
            raise RuntimeError('No PulseAudio stream for test player PID ' + str(process.pid))

        async def tap(name, seconds=.08):
            key(d, name, True)
            try: await asyncio.sleep(seconds)
            finally: key(d, name, False)
            await asyncio.sleep(.2)

        async def button(name):
            for _ in range(35):
                if snapshot()['session']['focused'] == name:
                    await tap('Return'); return
                await tap('Tab')
            raise RuntimeError('Could not focus ' + name)

        async def record(name, seconds, action=None, monitor=False):
            nonlocal recording
            path = OUT / (name + '.wav')
            recording = await asyncio.create_subprocess_exec('/usr/bin/ffmpeg', '-v', 'error', '-y', '-f', 'pulse',
                '-i', sink + '.monitor', '-t', str(seconds), '-ar', '48000', '-ac', '2', str(path))
            await asyncio.sleep(.4)
            if action: await action()
            wraps = 0
            last = next(s['time'] for s in snapshot()['audio']['sources'] if s['group'] == 'Music')
            while recording.returncode is None:
                try: await asyncio.wait_for(recording.wait(), timeout=.3)
                except asyncio.TimeoutError: pass
                if monitor:
                    s = snapshot()
                    music = next(s for s in s['audio']['sources'] if s['group'] == 'Music')
                    assert music['playing'], 'Music stopped'
                    assert s['session']['state'] == 'Play', 'Player lost focus during music check'
                    if music['time'] < last - 1: wraps += 1
                    last = music['time']
            assert recording.returncode == 0
            recording = None
            with wave.open(str(path)) as wav:
                values = array.array('h', wav.readframes(wav.getnframes()))
            rms = math.sqrt(sum(float(x)*x for x in values)/len(values))/32768
            peak = max(abs(x) for x in values)/32768
            state = snapshot()
            result = {'name': name, 'rms': rms, 'peak': peak, 'musicWraps': wraps,
                'state': state['session']['state'], 'audio': state['audio']}
            # Preserve a compact audition file; measurements above use captured PCM.
            audition = path.with_suffix('.ogg')
            subprocess.run(['/usr/bin/ffmpeg', '-v', 'error', '-y', '-i', str(path),
                '-c:a', 'libvorbis', '-q:a', '5', str(audition)], check=True)
            path.unlink()
            result['recording'] = audition.name
            report['recordings'].append(result)
            print(name, 'RMS', round(rms, 5), 'peak', round(peak, 4), 'wraps', wraps, flush=True)
            assert peak < .98, 'Output clipping'
            return result

        await asyncio.sleep(3)
        await route_player_audio()
        if snapshot()['session']['state'] == 'Paused': await tap('Escape')
        s = snapshot()
        sources = s['audio']['sources']
        assert len(sources) == 8, sources
        assert sum(bool(x['loop'] and x['playing']) for x in sources) == 5
        assert all(x['clip'] for x in sources)
        async with Client() as client:
            r = await record('capture-routing', 1)
            assert r['rms'] > .005, 'Capture routing is silent'
            r = await record('music-and-wind-loop', 42, monitor=True)
            assert r['rms'] > .005 and r['musicWraps'] >= 1
            before = snapshot()['audio']['StepCount']
            r = await record('walking-footsteps', 4, lambda: tap('w', 3))
            assert r['audio']['StepCount'] > before + 3 and r['rms'] > .005
            await client.command({'action': 'goto', 'landmark': 'basic_general'})
            await asyncio.sleep(.5)
            r = await record('market', 4)
            assert r['rms'] > .005
            await tap('e'); await button('choice0')
            before = snapshot()['audio']['TradeCount']
            r = await record('buy-flask', 2, lambda: button('buy0'))
            assert r['audio']['TradeCount'] == before + 1
            r = await record('sell-scrap', 2, lambda: button('sell2'))
            assert r['audio']['TradeCount'] == before + 2
            shop_music = next(s for s in r['audio']['sources'] if s['group'] == 'Music')
            assert abs(shop_music['volume'] - .65*.65) < .015, 'Dialogue/shop music did not soften'
            await tap('Escape')
            await client.command({'action': 'goto', 'landmark': 'lattice_jack'})
            await asyncio.sleep(.5)
            await record('lattice-hum', 3)
            r = await record('lattice-activation', 3, lambda: tap('e'))
            assert r['audio']['TravelOpenCount'] == 1
            grid_music = next(s for s in r['audio']['sources'] if s['group'] == 'Music')
            assert abs(grid_music['volume'] - .65*.4) < .015, 'Travel music did not soften'
            clicks = r['audio']['ClickCount']
            r = await record('lattice-link', 3, lambda: button('node0'))
            assert r['audio']['TravelLinkCount'] == 1 and snapshot()['session']['linked']
            assert r['audio']['ClickCount'] == clicks + 1, 'Repeated cue during UI/progress updates'
            await tap('Escape')
            r = await record('ring-offline', 3, lambda: client.command({'action': 'goto', 'landmark': 'ring_gate'}))
            assert r['audio']['UnavailableCount'] > 0
            await tap('Escape'); await asyncio.sleep(.8)
            before = next(s['time'] for s in snapshot()['audio']['sources'] if s['group'] == 'Music')
            r = await record('paused', 2)
            after = next(s['time'] for s in snapshot()['audio']['sources'] if s['group'] == 'Music')
            assert r['audio']['paused'] and r['rms'] < .00001
            assert abs(after-before) < .05, 'Paused music timeline moved'
            await button('mute'); await button('resume'); await asyncio.sleep(.8)
            r = await record('muted', 2)
            assert r['audio']['volume'] == 0 and r['rms'] < .00001
            await tap('Escape'); await button('mute'); await button('resume')
            r = await record('restored', 3)
            assert r['audio']['volume'] == 1 and r['rms'] > .005
            await client.command({'action': 'capture', 'name': 'audio-scene'})
            await client.command({'action': 'quit'})
        await asyncio.to_thread(process.wait, timeout=15)
        log = (OUT / 'Player.log').read_text()
        assert not any(x in log for x in ('Exception:', 'NullReferenceException', 'FMOD error', 'Error loading'))
        # Confirm that the release build also ships and plays the same offline audio.
        process = subprocess.Popen([str(ROOT / 'AthenHill/Builds/Linux/AthenHill.x86_64'),
            '-force-glcore', '-screen-fullscreen', '0', '-screen-width', '1920', '-screen-height', '1080',
            '-logFile', str(OUT / 'release-Player.log')], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        os.environ['ATHEN_NATIVE_PID'] = str(process.pid)
        await asyncio.sleep(6)
        focus()
        await asyncio.sleep(2)
        await route_player_audio()
        release_pcm = OUT / 'release-startup.wav'
        recording = await asyncio.create_subprocess_exec('/usr/bin/ffmpeg', '-v', 'error', '-y',
            '-f', 'pulse', '-i', sink + '.monitor', '-t', '5', '-ar', '48000', '-ac', '2', str(release_pcm))
        assert await recording.wait() == 0
        recording = None
        with wave.open(str(release_pcm)) as wav:
            values = array.array('h', wav.readframes(wav.getnframes()))
        rms = math.sqrt(sum(float(x)*x for x in values)/len(values))/32768
        peak = max(abs(x) for x in values)/32768
        assert rms > .005 and peak < .98, 'Release sound output missing or clipping'
        release_log = (OUT / 'release-Player.log').read_text()
        assert not any(x in release_log for x in ('Exception:', 'NullReferenceException', 'FMOD error', 'Error loading'))
        subprocess.run(['/usr/bin/ffmpeg', '-v', 'error', '-y', '-i', str(release_pcm),
            '-c:a', 'libvorbis', '-q:a', '5', str(release_pcm.with_suffix('.ogg'))], check=True)
        release_pcm.unlink()
        report['release'] = {'rms': rms, 'peak': peak, 'recording': 'release-startup.ogg', 'audioPlays': True}
        report['complete'] = True
        print('PASS: music loop, footsteps, market/devices, trades, travel, pause, mute and restore', flush=True)
    finally:
        if recording and recording.returncode is None:
            recording.terminate(); await recording.wait()
        if process and process.poll() is None:
            process.terminate(); process.wait(timeout=10)
        command('pactl', 'unload-module', module)
        (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


asyncio.run(main())

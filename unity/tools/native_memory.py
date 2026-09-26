"""Collect separate Unity, OS and driver memory evidence outside timed routes."""
import json
import os
import pathlib
import subprocess
import time
import xml.etree.ElementTree as ET


async def snapshot(client, folder):
    folder = pathlib.Path(folder)
    await client.command({'action': 'memorySnapshot'})
    result = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'unity': json.loads((folder / 'memory.json').read_text()),
              'pid': int(os.environ['ATHEN_NATIVE_PID']), 'process': None, 'driver': None}
    try:
        text = pathlib.Path('/proc') / str(result['pid']) / 'status'
        wanted = {'VmRSS', 'VmHWM', 'VmSize', 'VmPeak', 'VmSwap'}
        result['process'] = {key: value.strip() for line in text.read_text().splitlines()
                             if ':' in line for key, value in [line.split(':', 1)] if key in wanted}
    except (OSError, ValueError) as error:
        result['processUnavailable'] = str(error)
    try:
        command = subprocess.run(['nvidia-smi', '-q', '-x'], capture_output=True, text=True, timeout=8, check=True)
        data = ET.fromstring(command.stdout)
        cards = []
        for gpu in data.findall('gpu'):
            processes = [p for p in gpu.findall('./processes/process_info') if p.findtext('pid') == str(result['pid'])]
            cards.append({'name': gpu.findtext('product_name'),
                          'totalFramebufferMemory': gpu.findtext('./fb_memory_usage/total'),
                          'usedFramebufferMemoryAllProcesses': gpu.findtext('./fb_memory_usage/used'),
                          'nativeProcessUsedMemory': [p.findtext('used_memory') for p in processes] or None})
        result['driver'] = {'version': data.findtext('driver_version'), 'gpus': cards,
                            'scope': 'Driver framebuffer counters. Total used includes desktop/other processes; native allocation is null if the driver omits this graphics PID.'}
    except (OSError, ValueError, subprocess.SubprocessError, ET.ParseError) as error:
        result['driverUnavailable'] = str(error)
    return result

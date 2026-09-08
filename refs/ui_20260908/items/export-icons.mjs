import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '../../..');
const manifest = JSON.parse(fs.readFileSync(path.join(import.meta.dirname, 'manifest.json'), 'utf8'));
for (const item of manifest.icons) {
  const raw = path.join(root, item.rawPath);
  const runtime = path.join(root, item.runtimePath);
  if (!fs.existsSync(raw)) fs.copyFileSync(item.generatedPath, raw);
  if (!fs.existsSync(runtime)) execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-n', '-i', raw, '-vf', 'scale=192:192:flags=lanczos', '-frames:v', '1', '-pix_fmt', 'rgba', runtime]);
  const rgba = execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', runtime, '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], { maxBuffer: 1024 * 1024 });
  let transparent = 0, partial = 0, opaque = 0;
  for (let i = 3; i < rgba.length; i += 4) {
    if (rgba[i] === 0) transparent++;
    else if (rgba[i] === 255) opaque++;
    else partial++;
  }
  if (!transparent || !opaque) throw new Error(`${item.name}: missing transparency or opaque object pixels`);
  console.log(`${item.name}: 192x192 RGBA; alpha transparent=${transparent}, partial=${partial}, opaque=${opaque}`);
}

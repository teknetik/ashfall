export type AudioGroup = 'master' | 'ambience' | 'sfx' | 'ui';
export interface AudioMotion { speed: number; grounded: boolean; travelDistance: number }
type SoundId = 'desert_bed' | 'stone_step' | 'terminal_click' | 'transport_hum';
type LoopId = Extract<SoundId, 'desert_bed' | 'transport_hum'>;
type Voice = { source: AudioBufferSourceNode; gain: GainNode };

const FILES: Record<SoundId, string> = {
  desert_bed: 'desert-bed-mix.mp3', stone_step: 'stone-step-mix.mp3',
  terminal_click: 'terminal-click-mix.mp3', transport_hum: 'transport-hum-mix.mp3',
};
const DEFAULT_VOLUMES: Record<AudioGroup, number> = { master: .8, ambience: .7, sfx: .8, ui: .7 };

/** Local generated assets only. Call unlock() directly from a trusted gesture. */
export class GameAudio {
  private context?: AudioContext;
  private readonly buffers = new Map<SoundId, AudioBuffer>();
  private readonly groups = new Map<AudioGroup, GainNode>();
  private readonly loops = new Map<LoopId, Voice>();
  private readonly voices = new Set<Voice>();
  private readonly volumes = { ...DEFAULT_VOLUMES };
  private readonly loading = new AbortController();
  private pending?: Promise<void>;
  private state: 'locked' | 'loading' | 'ready' | 'error' | 'disposed' = 'locked';
  private muted = false;
  private paused = false;
  private hidden = document.hidden;
  private travelGain = 0;
  private stepDistance = 0;
  private lastStep = -Infinity;
  private lastClick = -Infinity;
  private stepCount = 0;
  private clickCount = 0;
  private error: string | null = null;
  private readonly onVisibility = () => { this.hidden = document.hidden; this.syncPlayback(); };

  constructor() { document.addEventListener('visibilitychange', this.onVisibility); }

  async unlock() {
    if (this.state === 'disposed') throw new Error('Game audio is disposed.');
    if (!this.context) {
      const AudioContextType = window.AudioContext
        ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioContextType) throw new Error('Web Audio is unavailable in this browser.');
      this.context = new AudioContextType();
      for (const name of Object.keys(this.volumes) as AudioGroup[]) {
        const gain = this.context.createGain();
        gain.gain.value = name === 'master' && this.muted ? 0 : this.volumes[name];
        this.groups.set(name, gain);
      }
      this.groups.get('master')!.connect(this.context.destination);
      for (const name of ['ambience', 'sfx', 'ui'] as const) this.groups.get(name)!.connect(this.groups.get('master')!);
    }
    // Start resume synchronously in the gesture, before waiting for any network.
    await this.context.resume();
    if (this.loading.signal.aborted) return;
    await (this.pending ??= this.load(this.context));
    this.syncPlayback();
  }

  private async load(context: AudioContext) {
    this.state = 'loading';
    const base = `${import.meta.env.BASE_URL}assets/audio/`;
    try {
      const manifestResponse = await fetch(`${base}manifest.json`, { signal: this.loading.signal });
      if (!manifestResponse.ok) throw new Error(`Audio manifest load failed (${manifestResponse.status}).`);
      const manifest: { status?: string; assets?: Array<{ id: string; file: string; status: string }> } = await manifestResponse.json();
      if (manifest.status !== 'generated' || !Array.isArray(manifest.assets)) throw new Error('Generated game audio is not available yet.');
      await Promise.all((Object.keys(FILES) as SoundId[]).map(async (id) => {
        if (!manifest.assets!.some((asset) => asset.id === id && asset.file === FILES[id] && asset.status === 'generated')) {
          throw new Error(`Audio manifest is missing ${id}.`);
        }
        const response = await fetch(`${base}${FILES[id]}`, { signal: this.loading.signal });
        if (!response.ok) throw new Error(`Audio asset load failed (${response.status}): ${FILES[id]}.`);
        const buffer = await context.decodeAudioData(await response.arrayBuffer());
        this.loading.signal.throwIfAborted();
        if (!Number.isFinite(buffer.duration) || buffer.duration <= 0) throw new Error(`Audio decoded empty: ${FILES[id]}.`);
        this.buffers.set(id, buffer);
      }));
      this.loading.signal.throwIfAborted();
      this.state = 'ready';
    } catch (error) {
      if (!this.loading.signal.aborted) {
        this.state = 'error';
        this.error = error instanceof Error ? error.message : 'Audio load failed.';
        this.loading.abort();
        this.buffers.clear();
      }
      throw error;
    }
  }

  setMuted(value: boolean) {
    this.muted = value;
    this.applyVolume('master');
  }

  setVolume(group: AudioGroup, value: number) {
    if (!Object.hasOwn(this.volumes, group) || !Number.isFinite(value)) throw new Error('Audio volume requires a valid group and finite value.');
    this.volumes[group] = Math.max(0, Math.min(1, value));
    this.applyVolume(group);
  }

  private applyVolume(group: AudioGroup) {
    const gain = this.groups.get(group);
    if (!gain || !this.context || this.state === 'disposed') return;
    gain.gain.setTargetAtTime(group === 'master' && this.muted ? 0 : this.volumes[group], this.context.currentTime, .02);
  }

  setPaused(value: boolean) {
    this.paused = value;
    this.stepDistance = 0;
    this.syncPlayback();
  }

  private syncPlayback() {
    const context = this.context;
    if (!context || this.state === 'disposed' || this.state === 'error') return;
    if (this.paused || this.hidden) {
      this.stopAll();
      void context.suspend().catch((error: unknown) => this.recordError(error));
      return;
    }
    if (this.state !== 'ready') return;
    void context.resume().then(() => {
      if (this.state !== 'ready' || this.paused || this.hidden || context.state !== 'running') return;
      if (!this.loops.has('desert_bed')) this.startLoop('desert_bed', .7);
      if (!this.loops.has('transport_hum')) this.startLoop('transport_hum', this.travelGain);
    }).catch((error: unknown) => this.recordError(error));
  }

  private startLoop(id: LoopId, volume: number) {
    const voice = this.createVoice(id, 'ambience', volume);
    if (!voice) return;
    voice.source.loop = true;
    this.loops.set(id, voice);
    voice.source.start();
  }

  private createVoice(id: SoundId, group: Exclude<AudioGroup, 'master'>, volume: number): Voice | undefined {
    const context = this.context, buffer = this.buffers.get(id);
    if (!context || !buffer || this.state !== 'ready' || this.paused || this.hidden || context.state !== 'running') return;
    const source = context.createBufferSource(), gain = context.createGain();
    source.buffer = buffer;
    gain.gain.value = volume;
    source.connect(gain).connect(this.groups.get(group)!);
    const voice = { source, gain };
    this.voices.add(voice);
    source.onended = () => this.releaseVoice(voice);
    return voice;
  }

  /** Feed actual corrected motion and distance to the nearest travel terminal. */
  update(dt: number, motion: AudioMotion) {
    if (!Number.isFinite(dt) || dt < 0 || !Number.isFinite(motion.speed)
      || (!Number.isFinite(motion.travelDistance) && motion.travelDistance !== Infinity)
      || motion.travelDistance < 0) throw new Error('Audio motion requires valid delta time, speed and travel distance.');
    this.travelGain = .55 * Math.pow(Math.max(0, 1 - motion.travelDistance / 14), 2);
    const hum = this.loops.get('transport_hum');
    if (hum && this.context) hum.gain.gain.setTargetAtTime(this.travelGain, this.context.currentTime, .12);
    if (this.state !== 'ready' || this.paused || this.hidden || this.muted || !motion.grounded || motion.speed < .12) {
      this.stepDistance = 0;
      return;
    }
    this.stepDistance += Math.max(0, motion.speed) * Math.min(dt, .1);
    const stride = motion.speed > 4.5 ? 1.45 : .95;
    if (this.stepDistance >= stride && this.context && this.context.currentTime - this.lastStep >= .2) {
      this.stepDistance %= stride;
      const voice = this.createVoice('stone_step', 'sfx', .5);
      if (!voice) return;
      this.lastStep = this.context.currentTime;
      // Alternate a small deterministic pitch offset to soften repetition.
      voice.source.playbackRate.value = ++this.stepCount % 2 ? .97 : 1.03;
      voice.source.start();
    }
  }

  terminalClick() {
    if (!this.context || this.muted || this.context.currentTime - this.lastClick < .08) return;
    const voice = this.createVoice('terminal_click', 'ui', .55);
    if (!voice) return;
    this.lastClick = this.context.currentTime;
    this.clickCount++;
    voice.source.start();
  }

  private releaseVoice(voice: Voice) {
    voice.source.onended = null;
    voice.source.disconnect();
    voice.gain.disconnect();
    this.voices.delete(voice);
    for (const [id, loop] of this.loops) if (loop === voice) this.loops.delete(id);
  }

  private stopAll() {
    for (const voice of [...this.voices]) {
      voice.source.stop();
      this.releaseVoice(voice);
    }
  }

  private recordError(error: unknown) {
    if (this.state !== 'disposed') this.error = error instanceof Error ? error.message : 'Audio context transition failed.';
  }

  get diagnostics() {
    return { state: this.state, contextState: this.context?.state ?? 'uncreated', muted: this.muted,
      paused: this.paused, hidden: this.hidden, buffers: this.buffers.size, loops: this.loops.size,
      voices: this.voices.size, steps: this.stepCount, clicks: this.clickCount, travelGain: this.travelGain,
      volumes: { ...this.volumes }, error: this.error };
  }

  dispose() {
    if (this.state === 'disposed') return;
    this.state = 'disposed';
    this.loading.abort();
    document.removeEventListener('visibilitychange', this.onVisibility);
    this.stopAll();
    this.buffers.clear();
    for (const gain of this.groups.values()) gain.disconnect();
    this.groups.clear();
    if (this.context && this.context.state !== 'closed') void this.context.close().catch(() => {});
  }
}

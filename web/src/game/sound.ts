// Sound effects and music (files in public/sfx, from the Mixkit free library).
// Effects are decoded once into Web Audio buffers and played with a little pitch/volume
// variation so repeated hits don't sound robotic. Music streams from <audio> elements and
// crossfades between the menu and battle tracks. Volumes are saved per browser.

export type MusicTrack = "menu" | "battle" | "";

const STORE = "fr-volume";
const MUSIC: Record<Exclude<MusicTrack, "">, string> = { menu: "music_menu", battle: "music_battle" };

// INDEPENDENT_AUDIO_BUSES_V1
// Music uses HTMLAudioElement; general SFX and combat feedback use separate Web Audio buses.
interface Volumes { master: number; sfx: number; music: number; combat: number }
const COMBAT_SOUNDS = new Set(["clash", "parry", "block", "guard_break"]);

/**
 * Longest an effect may ring (seconds) before it fades out. Library sounds often have long
 * tails (some are 10-20 s ambiences); this keeps every effect short and punchy.
 */
const DEFAULT_MAX = 1.6;
const MAX_LEN: Record<string, number> = {
  explosion: 2.5, thunder: 2.5, meteor: 2.2, rocks: 1.8, slam: 2, ready: 1.5, fight: 2.5,
  victory: 5, defeat: 5, wave: 4, heal: 2.5, burn: 1.5, shock: 1.2, water: 1.6, splash: 1.4, cast: 1.2,
  rage: 1.8, teleport: 1.4, ko: 2,
};

class SoundEngine {
  vol: Volumes = { master: 0.8, sfx: 0.9, music: 0.45, combat: 1 };
  private ctx: AudioContext | null = null;
  private out: GainNode | null = null;
  private combatOut: GainNode | null = null;
  private buffers = new Map<string, AudioBuffer | null>();
  private loading = new Map<string, Promise<AudioBuffer | null>>();
  private lastPlay = new Map<string, number>();
  private track: MusicTrack = "";
  private music: HTMLAudioElement | null = null;
  private fading: HTMLAudioElement[] = [];
  private unlocked = false;

  constructor() {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(STORE);
      if (raw) this.vol = { ...this.vol, ...JSON.parse(raw) };
    } catch {}
    // Browsers only allow audio after a user gesture.
    const unlock = () => {
      this.unlocked = true;
      this.context()?.resume().catch(() => {});
      if (this.track && this.music?.paused) this.music.play().catch(() => {});
    };
    window.addEventListener("pointerdown", unlock, { capture: true });
    window.addEventListener("keydown", unlock, { capture: true });
  }

  private context(): AudioContext | null {
    if (this.ctx) return this.ctx;
    const AC = typeof window !== "undefined" ? (window.AudioContext || (window as any).webkitAudioContext) : null;
    if (!AC) return null;
    this.ctx = new AC();
    this.out = this.ctx.createGain();
    this.out.gain.value = this.vol.master * this.vol.sfx;
    this.out.connect(this.ctx.destination);
    this.combatOut = this.ctx.createGain();
    this.combatOut.gain.value = this.vol.master * this.vol.combat;
    this.combatOut.connect(this.ctx.destination);
    return this.ctx;
  }

  private load(name: string): Promise<AudioBuffer | null> {
    const ctx = this.context();
    if (!ctx) return Promise.resolve(null);
    let p = this.loading.get(name);
    if (!p) {
      p = fetch(`/sfx/${name}.mp3`)
        .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(r.statusText))))
        .then((b) => ctx.decodeAudioData(b))
        .then((buf) => { this.buffers.set(name, buf); return buf; })
        .catch(() => { this.buffers.set(name, null); return null; });
      this.loading.set(name, p);
    }
    return p;
  }

  /** Decode sounds ahead of time so the first hit isn't silent. */
  preload(names: string[]) { if (this.unlocked || this.ctx) names.forEach((n) => this.load(n)); }

  /**
   * Play an effect. `vol` 0..1 scales it; `vary` randomizes pitch (+-) for variety. The same
   * sound is skipped if it played in the last 40 ms (a multi-hit skill won't stack 8 copies).
   */
  play(name: string, vol = 1, vary = 0.06) {
    const combat = COMBAT_SOUNDS.has(name);
    if (!name || this.vol.master * (combat ? this.vol.combat : this.vol.sfx) <= 0) return;
    const now = performance.now();
    if (now - (this.lastPlay.get(name) ?? -1e9) < 40) return;
    this.lastPlay.set(name, now);
    const ctx = this.context();
    if (!ctx || ctx.state === "closed") return;
    const start = (buf: AudioBuffer | null) => {
      const bus = combat ? this.combatOut : this.out;
      if (!buf || !bus) return;
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.playbackRate.value = 1 + (Math.random() * 2 - 1) * vary;
      const g = ctx.createGain();
      const v = Math.min(vol, 1.5);
      const t0 = ctx.currentTime;
      const max = MAX_LEN[name] ?? DEFAULT_MAX;
      g.gain.setValueAtTime(v, t0);
      src.connect(g).connect(bus);
      src.start(t0);
      if (buf.duration / src.playbackRate.value > max) {
        // Fade out over the last 0.3 s, then stop.
        g.gain.setValueAtTime(v, t0 + max - 0.3);
        g.gain.linearRampToValueAtTime(0, t0 + max);
        src.stop(t0 + max + 0.02);
      }
    };
    const buf = this.buffers.get(name);
    if (buf !== undefined) start(buf);
    else this.load(name).then((b) => { if (performance.now() - now < 250) start(b); });
  }

  /** Switch music (crossfade); "" stops it. */
  setMusic(track: MusicTrack) {
    if (typeof window === "undefined" || track === this.track) return;
    this.track = track;
    if (this.music) { this.fading.push(this.music); this.music = null; }
    if (track) {
      const a = new Audio(`/sfx/${MUSIC[track]}.mp3`);
      a.loop = true;
      a.volume = 0;
      this.music = a;
      if (this.unlocked) a.play().catch(() => {});
    }
    this.fade();
  }

  private fadeTimer: ReturnType<typeof setInterval> | null = null;
  private fade() {
    if (this.fadeTimer) return;
    this.fadeTimer = setInterval(() => {
      const target = this.vol.master * this.vol.music;
      let busy = false;
      if (this.music) {
        const v = this.music.volume;
        this.music.volume = Math.abs(target - v) < 0.03 ? target : v + Math.sign(target - v) * 0.03;
        busy ||= this.music.volume !== target;
      }
      this.fading = this.fading.filter((a) => {
        a.volume = Math.max(a.volume - 0.04, 0);
        if (a.volume <= 0) { a.pause(); return false; }
        busy = true;
        return true;
      });
      if (!busy && this.fadeTimer) { clearInterval(this.fadeTimer); this.fadeTimer = null; }
    }, 50);
  }

  setVolume(kind: keyof Volumes, v: number) {
    this.vol = { ...this.vol, [kind]: Math.max(0, Math.min(1, v)) };
    try { localStorage.setItem(STORE, JSON.stringify(this.vol)); } catch {}
    if (this.out) this.out.gain.value = this.vol.master * this.vol.sfx;
    if (this.combatOut) this.combatOut.gain.value = this.vol.master * this.vol.combat;
    this.fade();
  }
}

export const Sound = new SoundEngine();

/** Effects every match needs, decoded when a match starts. */
export const MATCH_SOUNDS = ["swing", "swing2", "swing_heavy", "whoosh_light", "hit_blade", "hit_blade2", "hit_blunt",
  "hit_blunt2", "hit_kick", "hit_heavy", "crit", "block", "parry", "guard_break", "clash", "dash", "jump", "land", "ko",
  "ready", "fight", "victory", "defeat"];

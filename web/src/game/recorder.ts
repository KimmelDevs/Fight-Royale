// FR_VIDEO_RECORDER_V1 — records CPU vs CPU matches to a video file you can upload to YouTube.
//
// Two capture modes:
//   "tab"    (preferred) browser screen-capture of THIS tab: includes the HUD, health bars, banners,
//            music and sound effects. The browser asks for permission once per session.
//   "canvas" fallback when screen capture is unavailable/declined: only the 3D canvas + sound effects
//            (no HUD, no music).
import { Sound } from "./sound";

export type RecMode = "tab" | "canvas";

const KEY = "fr-autorec";
export const autoRecordEnabled = (): boolean => {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
};
export const setAutoRecord = (on: boolean) => {
  try { localStorage.setItem(KEY, on ? "1" : "0"); } catch {}
};

const MIMES = [
  "video/webm;codecs=vp9,opus",
  "video/webm;codecs=vp8,opus",
  "video/webm",
  "video/mp4",
];
const pickMime = (): string => {
  if (typeof MediaRecorder === "undefined") return "";
  return MIMES.find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
};

class MatchRecorder {
  mode: RecMode = "canvas";
  /** Called when a recording ends by itself (e.g. the user pressed the browser's "Stop sharing"). */
  onUnexpectedStop: ((blob: Blob) => void) | null = null;

  private display: MediaStream | null = null;
  private pending: Promise<boolean> | null = null;
  private rec: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private stopResolver: ((b: Blob | null) => void) | null = null;
  private t0 = 0;
  private mime = "";

  get supported(): boolean { return typeof MediaRecorder !== "undefined" && !!pickMime(); }
  get canTabCapture(): boolean {
    return typeof navigator !== "undefined" && !!navigator.mediaDevices?.getDisplayMedia;
  }
  get recording(): boolean { return this.rec?.state === "recording"; }
  elapsed(): number { return this.recording ? (performance.now() - this.t0) / 1000 : 0; }

  private tabLive(): boolean {
    return !!this.display?.getVideoTracks().some((t) => t.readyState === "live");
  }

  /**
   * Ask the browser to share this tab. Must be called from a click / key handler (user gesture).
   * The stream is kept for the whole session so later fights record without asking again.
   */
  prepareTab(): Promise<boolean> {
    if (this.tabLive()) return Promise.resolve(true);
    if (this.pending) return this.pending;
    if (!this.canTabCapture) return Promise.resolve(false);
    const opts: any = {
      video: { frameRate: { ideal: 60, max: 60 } },
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
      preferCurrentTab: true,
      selfBrowserSurface: "include",
      surfaceSwitching: "exclude",
      systemAudio: "include",
    };
    this.pending = navigator.mediaDevices.getDisplayMedia(opts)
      .then((s) => {
        this.display = s;
        s.getVideoTracks()[0]?.addEventListener("ended", () => { if (this.display === s) this.display = null; });
        return true;
      })
      .catch(() => false)
      .finally(() => { this.pending = null; });
    return this.pending;
  }

  /** Start recording. Returns the capture mode used, or null if recording is impossible. */
  async start(canvas: HTMLCanvasElement | null): Promise<RecMode | null> {
    if (this.recording) return this.mode;
    if (!this.supported) return null;
    if (this.pending) await this.pending;

    let stream: MediaStream;
    let mode: RecMode;
    if (this.tabLive()) {
      stream = this.display!;
      mode = "tab";
    } else {
      if (!canvas || typeof (canvas as any).captureStream !== "function") return null;
      const video = (canvas as any).captureStream(60) as MediaStream;
      const audio = Sound.captureStream();
      stream = new MediaStream([...video.getVideoTracks(), ...(audio ? audio.getAudioTracks() : [])]);
      mode = "canvas";
    }

    this.mime = pickMime();
    this.chunks = [];
    const rec = new MediaRecorder(stream, {
      mimeType: this.mime || undefined,
      videoBitsPerSecond: 16000000,
      audioBitsPerSecond: 192000,
    });
    rec.ondataavailable = (e) => { if (e.data && e.data.size) this.chunks.push(e.data); };
    rec.onstop = () => {
      const type = (this.mime.split(";")[0]) || "video/webm";
      const blob = this.chunks.length ? new Blob(this.chunks, { type }) : null;
      this.chunks = [];
      this.rec = null;
      const resolve = this.stopResolver;
      this.stopResolver = null;
      if (resolve) resolve(blob);
      else if (blob) this.onUnexpectedStop?.(blob);
    };
    rec.start(1000);
    this.rec = rec;
    this.mode = mode;
    this.t0 = performance.now();
    return mode;
  }

  /** Stop and resolve with the finished video (null if nothing was recorded). */
  stop(): Promise<Blob | null> {
    const rec = this.rec;
    if (!rec || rec.state === "inactive") return Promise.resolve(null);
    return new Promise((resolve) => {
      this.stopResolver = resolve;
      try { rec.stop(); } catch { this.stopResolver = null; resolve(null); }
    });
  }

  /** Download the video through the browser. */
  save(blob: Blob, baseName: string) {
    const ext = blob.type.includes("mp4") ? "mp4" : "webm";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${baseName}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  /** End the screen share (call when leaving the match screen). */
  release() {
    this.display?.getTracks().forEach((t) => t.stop());
    this.display = null;
  }
}

export const Recorder = new MatchRecorder();

#!/usr/bin/env python3
"""
FR_VIDEO_RECORDER_V1 installer — adds video recording to Fight Royale's CPU vs CPU (1v1) mode.

What it adds
  * src/game/recorder.ts      (new)  MediaRecorder wrapper: tab capture (HUD + all audio) with a
                                      canvas-only fallback, auto-saves a .webm named after the matchup.
  * src/game/sound.ts         (edit) exposes the sound-effect bus so canvas-only mode has audio.
  * src/ui/GameView.tsx       (edit) Record button + F9 hotkey in spectator matches, auto-stop 5 s after
                                      the winner is shown, auto-restart on Rematch, save on leaving.
  * src/ui/WatchSelect.tsx    (edit) "Auto-record every fight" checkbox on the matchup screen.
  * src/app/globals.css       (edit) styling for the record button.

Usage (run from the project root, the folder that contains src/):
    python install_video_recorder.py            # install
    python install_video_recorder.py --dry-run  # check everything matches, write nothing
    python install_video_recorder.py --restore  # undo, using the newest backup this script made

Every touched file is backed up first to scripts/backups/video_recorder_<timestamp>/.
Nothing is written unless ALL edits can be applied cleanly.
"""
import datetime
import json
import os
import sys

MARK = "FR_VIDEO_RECORDER_V1"

# --------------------------------------------------------------------------------------
# New file: src/game/recorder.ts
# --------------------------------------------------------------------------------------
RECORDER_TS = r'''// FR_VIDEO_RECORDER_V1 — records CPU vs CPU matches to a video file you can upload to YouTube.
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
'''

# --------------------------------------------------------------------------------------
# CSS appended to globals.css
# --------------------------------------------------------------------------------------
CSS_ADD = '''

/* FR_VIDEO_RECORDER_V1 — record button on CPU vs CPU matches. */
.fr-rec-btn {
  position: absolute; left: 12px; bottom: 10px; z-index: 20;
  border: 1px solid rgba(255,120,120,.55); border-radius: 6px;
  padding: 5px 10px; background: rgba(40,8,12,.72);
  color: #ffd3d3; font-family: inherit; font-size: 11px; font-weight: 800; line-height: 1.2;
  cursor: pointer; pointer-events: auto; opacity: .85;
}
.fr-rec-btn:hover, .fr-rec-btn:focus-visible { opacity: 1; background: rgba(90,14,20,.92); }
.fr-rec-btn.on { background: rgba(160,16,24,.92); color: #fff; border-color: #ff6b6b; opacity: 1; }
@media (max-width: 700px) { .fr-rec-btn { left: 5px; bottom: 4px; font-size: 9px; padding: 3px 6px; } }
'''

# --------------------------------------------------------------------------------------
# Edits to existing files.  (path, anchor, replacement)  — anchor must occur exactly once.
# Line endings are handled automatically (files keep their original CRLF/LF style).
# --------------------------------------------------------------------------------------
SOUND = "src/game/sound.ts"
GAMEVIEW = "src/ui/GameView.tsx"
WATCH = "src/ui/WatchSelect.tsx"
CSS = "src/app/globals.css"

EDITS = [
    # ---- sound.ts: tap the SFX bus ----
    (SOUND,
     "  private combatOut: GainNode | null = null;\n",
     "  private combatOut: GainNode | null = null;\n"
     "  private tap: MediaStreamAudioDestinationNode | null = null; // FR_VIDEO_RECORDER_V1\n"),
    (SOUND,
     "    this.combatOut.connect(this.ctx.destination);\n    return this.ctx;\n",
     "    this.combatOut.connect(this.ctx.destination);\n"
     "    // FR_VIDEO_RECORDER_V1: extra copy of the sound effects for canvas-only recordings.\n"
     "    try {\n"
     "      this.tap = this.ctx.createMediaStreamDestination();\n"
     "      this.out.connect(this.tap);\n"
     "      this.combatOut.connect(this.tap);\n"
     "    } catch {}\n"
     "    return this.ctx;\n"),
    (SOUND,
     "  private load(name: string): Promise<AudioBuffer | null> {\n",
     "  /** FR_VIDEO_RECORDER_V1: sound-effect stream for the video recorder (music is not included). */\n"
     "  captureStream(): MediaStream | null {\n"
     "    this.context();\n"
     "    return this.tap?.stream ?? null;\n"
     "  }\n"
     "\n"
     "  private load(name: string): Promise<AudioBuffer | null> {\n"),

    # ---- GameView.tsx ----
    (GAMEVIEW,
     'import { Icon, skillIcon, charIcon } from "./icons";\n',
     'import { Icon, skillIcon, charIcon } from "./icons";\n'
     'import { Recorder, autoRecordEnabled, type RecMode } from "@/game/recorder"; // FR_VIDEO_RECORDER_V1\n'),

    (GAMEVIEW,
     '  useEffect(() => { Sound.setMusic("battle"); return () => Sound.setMusic("menu"); }, []);\n',
     '''  // FR_VIDEO_RECORDER_V1 — CPU vs CPU video recording.
  const [recMode, setRecMode] = useState<RecMode | null>(null);
  const recTimer = useRef<any>(null);
  const titleBefore = useRef(typeof document !== "undefined" ? document.title : "");
  const recFileName = () => {
    const names = (cfg.players ?? []).slice(0, 2).map((p: any) => String(p.name ?? "CPU").replace(/[^A-Za-z0-9]+/g, ""));
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, "0");
    const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
    return `FightRoyale_${names.join("_vs_") || "CPU"}_${stamp}`;
  };
  const finishRec = async () => {
    clearTimeout(recTimer.current);
    const blob = await Recorder.stop();
    setRecMode(null);
    document.title = titleBefore.current;
    if (blob) { Recorder.save(blob, recFileName()); toast("Video saved to your downloads"); }
  };
  const startRec = async () => {
    if (!cfg.spectator) return;
    clearTimeout(recTimer.current);
    if (Recorder.recording) await finishRec();
    const mode = await Recorder.start(canvas.current);
    setRecMode(mode);
    if (!mode) toast("Video recording is not supported in this browser");
    else if (mode === "canvas") toast("Recording the arena only (no HUD). Allow screen sharing to include the HUD.");
    else document.title = "● REC";
  };
  /** After a rematch: begin a fresh recording (auto mode) or close the previous one. */
  const onRestart = () => {
    if (!cfg.spectator) return;
    if (autoRecordEnabled()) startRec();
    else if (Recorder.recording) finishRec();
  };
  const toggleRec = () => {
    if (Recorder.recording) { finishRec(); return; }
    Recorder.prepareTab(); // must run inside the click / key press
    startRec();
  };

  useEffect(() => { Sound.setMusic("battle"); return () => Sound.setMusic("menu"); }, []);
'''),

    (GAMEVIEW,
     "    g.start();\n    const iv = setInterval(() => setHud(g.hud()), 80);\n",
     "    g.start();\n"
     "    // FR_VIDEO_RECORDER_V1\n"
     "    Recorder.onUnexpectedStop = (blob) => {\n"
     "      Recorder.save(blob, recFileName());\n"
     "      setRecMode(null);\n"
     "      document.title = titleBefore.current;\n"
     "      toast(\"Screen sharing ended: video saved\");\n"
     "    };\n"
     "    if (cfg.spectator && autoRecordEnabled()) startRec();\n"
     "    const iv = setInterval(() => setHud(g.hud()), 80);\n"),

    (GAMEVIEW,
     "        setOver({ text: e.text, sub: e.sub, color: e.color });\n",
     "        setOver({ text: e.text, sub: e.sub, color: e.color });\n"
     "        // FR_VIDEO_RECORDER_V1: keep rolling 5 s so the winner pose and highlights are in the video.\n"
     "        if (Recorder.recording) { clearTimeout(recTimer.current); recTimer.current = setTimeout(() => { finishRec(); }, 5000); }\n"),

    (GAMEVIEW,
     '      if (e.code === "Escape") { e.preventDefault(); const p = !g.paused; g.paused = p; setPausedState(p); }\n',
     '      if (e.code === "Escape") { e.preventDefault(); const p = !g.paused; g.paused = p; setPausedState(p); }\n'
     '      if (e.code === "F9" && cfg.spectator) { e.preventDefault(); toggleRec(); } // FR_VIDEO_RECORDER_V1\n'),

    (GAMEVIEW,
     "rankDone.current = false; g.restart(); }\n",
     "rankDone.current = false; g.restart(); onRestart(); }\n"),

    (GAMEVIEW,
     "rankDone.current = false; game.current?.restart(); };\n",
     "rankDone.current = false; game.current?.restart(); onRestart(); };\n"),

    (GAMEVIEW,
     '      window.removeEventListener("keydown", key);\n      g.dispose();\n',
     '      window.removeEventListener("keydown", key);\n'
     '      // FR_VIDEO_RECORDER_V1: leaving the match saves any recording in progress and ends screen sharing.\n'
     '      clearTimeout(recTimer.current);\n'
     '      Recorder.onUnexpectedStop = null;\n'
     '      document.title = titleBefore.current;\n'
     '      if (Recorder.recording) Recorder.stop().then((b) => { if (b) Recorder.save(b, recFileName()); Recorder.release(); });\n'
     '      else Recorder.release();\n'
     '      g.dispose();\n'),

    (GAMEVIEW,
     '      <div className="toasts">{toasts.map((t) => <div key={t.id} className="toast">{t.text}</div>)}</div>\n',
     '      <div className="toasts">{toasts.map((t) => <div key={t.id} className="toast">{t.text}</div>)}</div>\n'
     '      {/* FR_VIDEO_RECORDER_V1: hidden while tab-recording so the button never appears in the video */}\n'
     '      {cfg.spectator && recMode !== "tab" && (\n'
     '        <button type="button" className={"fr-rec-btn" + (recMode ? " on" : "")} onClick={toggleRec}\n'
     '          title="Record this match to a video file (F9)">\n'
     '          {recMode\n'
     '            ? `■ REC ${Math.floor(Recorder.elapsed() / 60)}:${String(Math.floor(Recorder.elapsed() % 60)).padStart(2, "0")} · stop`\n'
     '            : "⏺ Record (F9)"}\n'
     '        </button>\n'
     '      )}\n'),

    # ---- WatchSelect.tsx ----
    (WATCH,
     'import { useState } from "react";\n',
     'import { useEffect, useState } from "react";\n'),
    (WATCH,
     'import { CardRow, Showcase, RANDOM } from "./Select";\n',
     'import { CardRow, Showcase, RANDOM } from "./Select";\n'
     'import { Recorder, autoRecordEnabled, setAutoRecord } from "@/game/recorder"; // FR_VIDEO_RECORDER_V1\n'),
    (WATCH,
     "  const chosen = active === 0 ? left : right;\n",
     "  const chosen = active === 0 ? left : right;\n"
     "  // FR_VIDEO_RECORDER_V1\n"
     "  const [autoRec, setAutoRecState] = useState(false);\n"
     "  useEffect(() => { setAutoRecState(autoRecordEnabled()); }, []);\n"
     "  const toggleAutoRec = (on: boolean) => { setAutoRecState(on); setAutoRecord(on); };\n"),
    (WATCH,
     "  const start = () => {\n",
     "  const start = () => {\n"
     "    if (autoRec) Recorder.prepareTab(); // FR_VIDEO_RECORDER_V1: must be called inside this click\n"),
    (WATCH,
     '          <div className="row">\n            <button className="big ghost" onClick={onBack}>&lt; BACK</button>\n',
     '          {/* FR_VIDEO_RECORDER_V1 */}\n'
     '          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, fontWeight: 700, cursor: "pointer", margin: "0 0 8px" }}\n'
     '            title="Records every fight to a video file. Your browser asks once to share this tab; tick &quot;Share tab audio&quot; to capture the music.">\n'
     '            <input type="checkbox" checked={autoRec} onChange={(e) => toggleAutoRec(e.target.checked)} />\n'
     '            <span>⏺ Auto-record every fight (saves a video file)</span>\n'
     '          </label>\n'
     '          <div className="row">\n            <button className="big ghost" onClick={onBack}>&lt; BACK</button>\n'),
]

NEW_FILES = {"src/game/recorder.ts": RECORDER_TS}
APPENDS = {CSS: CSS_ADD}


# --------------------------------------------------------------------------------------
def read(path):
    with open(path, "rb") as f:
        raw = f.read().decode("utf-8")
    crlf = "\r\n" in raw
    return raw.replace("\r\n", "\n"), crlf


def write(path, text, crlf):
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))


def find_root():
    for cand in (os.getcwd(), os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if os.path.isfile(os.path.join(cand, "src", "game", "game.ts")):
            return cand
    sys.exit("Could not find the project root (a folder containing src/game/game.ts). "
             "cd into it and run the script again.")


def restore(root):
    base = os.path.join(root, "scripts", "backups")
    runs = sorted(d for d in os.listdir(base) if d.startswith("video_recorder_")) if os.path.isdir(base) else []
    if not runs:
        sys.exit("No video_recorder backup found in scripts/backups.")
    d = os.path.join(base, runs[-1])
    with open(os.path.join(d, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    for rel in man["modified"]:
        src = os.path.join(d, rel.replace("/", "__") + ".txt")
        with open(src, "rb") as f:
            data = f.read()
        with open(os.path.join(root, rel), "wb") as f:
            f.write(data)
        print("restored", rel)
    for rel in man["created"]:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            os.remove(p)
            print("removed ", rel)
    print("Restored from", d)


def main():
    root = find_root()
    if "--restore" in sys.argv:
        return restore(root)
    dry = "--dry-run" in sys.argv

    # Load + patch everything in memory first.
    files = {}
    for rel in {e[0] for e in EDITS} | set(APPENDS):
        files[rel] = read(os.path.join(root, rel))

    for rel in {e[0] for e in EDITS} | set(APPENDS):
        if MARK in files[rel][0]:
            sys.exit(f"{rel} already contains {MARK}: the recorder is already installed. "
                     f"Use --restore first if you want to reinstall.")
    for rel in NEW_FILES:
        if os.path.exists(os.path.join(root, rel)):
            sys.exit(f"{rel} already exists; refusing to overwrite it.")

    problems = []
    for rel, anchor, repl in EDITS:
        text, crlf = files[rel]
        n = text.count(anchor)
        if n != 1:
            problems.append(f"  {rel}: anchor found {n}x (expected 1):\n    {anchor.strip().splitlines()[0][:100]}")
            continue
        files[rel] = (text.replace(anchor, repl, 1), crlf)
    for rel, add in APPENDS.items():
        text, crlf = files[rel]
        files[rel] = (text.rstrip("\n") + "\n" + add, crlf)

    if problems:
        print("The project differs from what this installer expects; nothing was changed:\n")
        print("\n".join(problems))
        sys.exit(1)

    if dry:
        print("Dry run OK: all edits apply cleanly. Nothing written.")
        return

    # Backup.
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(root, "scripts", "backups", f"video_recorder_{ts}")
    os.makedirs(bdir, exist_ok=True)
    modified = sorted(files)
    for rel in modified:
        with open(os.path.join(root, rel), "rb") as f:
            data = f.read()
        with open(os.path.join(bdir, rel.replace("/", "__") + ".txt"), "wb") as f:
            f.write(data)
    with open(os.path.join(bdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "video_recorder", "modified": modified, "created": sorted(NEW_FILES)}, f, indent=2)

    # Write.
    for rel, (text, crlf) in files.items():
        write(os.path.join(root, rel), text, crlf)
        print("patched ", rel)
    for rel, text in NEW_FILES.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("created ", rel)
    print(f"\nDone. Backup: scripts/backups/video_recorder_{ts}\n"
          "Run your dev server (npm run dev) and open Watch CPU vs CPU.")


if __name__ == "__main__":
    main()

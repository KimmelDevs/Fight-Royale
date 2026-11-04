// Rewarded video ads. With NEXT_PUBLIC_GAM_REWARDED_UNIT set, uses Google Ad Manager's
// rewarded ads for web (GPT). With NEXT_PUBLIC_ADS_DEMO=1 (development), a fake 5-second ad
// plays so the diamond flow can be tested. Otherwise ads are unavailable.

const UNIT = process.env.NEXT_PUBLIC_GAM_REWARDED_UNIT ?? "";
const DEMO = process.env.NEXT_PUBLIC_ADS_DEMO === "1";

export const adsAvailable = () => !!UNIT || DEMO;
export const adsAreDemo = () => !UNIT && DEMO;

let gptLoaded: Promise<void> | null = null;
function loadGpt() {
  if (!gptLoaded) {
    gptLoaded = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://securepubads.g.doubleclick.net/tag/js/gpt.js";
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("Ad script blocked"));
      document.head.appendChild(s);
    });
  }
  return gptLoaded;
}

/** Plays a Google Ad Manager rewarded ad. Resolves true only if the reward was granted. */
async function playGam(): Promise<boolean> {
  await loadGpt();
  const w = window as any;
  w.googletag = w.googletag || { cmd: [] };
  const gt = w.googletag;
  return new Promise((resolve) => {
    gt.cmd.push(() => {
      const slot = gt.defineOutOfPageSlot(UNIT, gt.enums.OutOfPageFormat.REWARDED);
      if (!slot) { resolve(false); return; }
      slot.addService(gt.pubads());
      let granted = false;
      const done = (ok: boolean) => {
        gt.pubads().removeEventListener?.("rewardedSlotReady", onReady);
        gt.destroySlots([slot]);
        resolve(ok);
      };
      const onReady = (e: any) => { if (e.slot === slot) e.makeRewardedVisible(); };
      gt.pubads().addEventListener("rewardedSlotReady", onReady);
      gt.pubads().addEventListener("rewardedSlotGranted", (e: any) => { if (e.slot === slot) granted = true; });
      gt.pubads().addEventListener("rewardedSlotClosed", (e: any) => { if (e.slot === slot) done(granted); });
      gt.pubads().addEventListener("slotRenderEnded", (e: any) => { if (e.slot === slot && e.isEmpty) done(false); });
      gt.enableServices();
      gt.display(slot);
    });
  });
}

/**
 * Shows a rewarded ad. `demo` is called with a countdown setter so the UI can render the fake
 * ad; resolves true when the player earned the reward.
 */
export async function showRewardedAd(demo: (seconds: number) => void): Promise<boolean> {
  if (UNIT) return playGam();
  if (!DEMO) return false;
  for (let s = 5; s > 0; s--) {
    demo(s);
    await new Promise((r) => setTimeout(r, 1000));
  }
  demo(0);
  return true;
}

import { flushSync } from "react-dom";

/* Runs a state update inside a view transition, so the Reader's detail panel (.reader-panel)
   cross-fades while the page behind it stays put. `data-vt` takes the page itself out of the
   transition for the duration, so only the panel is captured (index.css). Where the API is
   missing, or `animate` is false, the update runs at once. The caller passes false for a
   keyboard step and for reduced motion. */
export function panelTransition(update: () => void, animate: boolean): void {
  if (!animate || !("startViewTransition" in document)) {
    update();
    return;
  }
  const root = document.documentElement;
  root.dataset.vt = "panel";
  const t = document.startViewTransition(() => flushSync(update));
  const done = () => {
    delete root.dataset.vt;
  };
  t.finished.then(done, done);
  // A hidden document skips the transition and rejects here. The update has still run.
  t.ready.catch(() => {});
}

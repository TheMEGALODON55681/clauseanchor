/* Pure helpers for the Reader. Both are tested without a DOM (reader.test.ts). */

/** Which tick a click at `y` means. `ats` are tick positions and `y` a click, both 0 to 1 down
 *  the strip, and `stripPx` is the strip's height. The nearest tick wins, so neighbours never
 *  share a hit area. A click more than `reachPx` from every tick means none, and gives -1. */
export function nearestMark(ats: number[], y: number, stripPx: number, reachPx = 12): number {
  if (stripPx <= 0) return -1;
  let best = -1;
  let bestPx = Infinity;
  ats.forEach((at, i) => {
    const px = Math.abs(at - y) * stripPx;
    if (px < bestPx) {
      best = i;
      bestPx = px;
    }
  });
  // The epsilon is for float error: 0.524 - 0.5 times 500 is 12.000000000000014.
  return bestPx <= reachPx + 1e-6 ? best : -1;
}

/** Stagger steps for rows that are new since the last render. Each new id gets the next step, and
 *  steps stop at `cap - 1`, so a burst of rows never waits longer than the cap allows. */
export function freshDelays(seen: ReadonlySet<string>, ids: Iterable<string>, cap = 6): Map<string, number> {
  const out = new Map<string, number>();
  for (const id of ids) if (!seen.has(id)) out.set(id, Math.min(out.size, cap - 1));
  return out;
}

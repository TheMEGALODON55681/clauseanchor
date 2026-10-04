/* Scroll reveal, once per element. No attribute means visible, so content shows
   without JavaScript and under reduced motion. The element is hidden only after
   an observer exists, and `index.css` styles the two states. */

export type ObserverLike = { observe(target: unknown): void; disconnect(): void };
export type ObserverFactory = (callback: (entries: { isIntersecting: boolean }[]) => void) => ObserverLike | null;

type Revealable = { dataset: Record<string, string | undefined> };

/** Returns a function that stops watching. */
export function revealOnce(el: Revealable, makeObserver: ObserverFactory, reduced: boolean): () => void {
  if (reduced) return () => {};
  const observer = makeObserver((entries) => {
    if (!entries.some((e) => e.isIntersecting)) return;
    el.dataset.reveal = "shown";
    observer?.disconnect();
  });
  if (!observer) return () => {};
  el.dataset.reveal = "pending";
  observer.observe(el);
  return () => observer.disconnect();
}

export const browserObserver: ObserverFactory = (callback) =>
  typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(callback, { rootMargin: "0px 0px -10% 0px" });

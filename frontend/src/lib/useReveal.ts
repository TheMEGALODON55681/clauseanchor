import { useLayoutEffect, useRef } from "react";
import { browserObserver, revealOnce } from "./reveal.ts";
import { useReducedMotion } from "./useMedia";

/** Attach the ref to an element that should rise into view once. */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const reduced = useReducedMotion();
  useLayoutEffect(() => (ref.current ? revealOnce(ref.current, browserObserver, reduced) : undefined), [reduced]);
  return ref;
}

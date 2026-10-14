import type { ReactNode } from "react";
import { useReveal } from "../lib/useReveal";

/* A real component shown as a specimen. It takes no input and is hidden from assistive
   technology, because the text beside it says the same thing in words. It rises into view once. */
export default function Specimen({ children }: { children: ReactNode }) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <div ref={ref} inert aria-hidden className="max-w-[400px]">
      {children}
    </div>
  );
}

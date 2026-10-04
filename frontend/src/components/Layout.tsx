import type { ReactNode } from "react";

/* Layout primitives. The margin column holds section marks and short notes,
   the main column is the reading measure, the aside holds the component that
   a section explains. Widths and breakpoints are in index.css. */

export function Container({ children }: { children: ReactNode }) {
  return <div className="container-page">{children}</div>;
}

export function MarginGrid({ margin, aside, children }: { margin?: ReactNode; aside?: ReactNode; children: ReactNode }) {
  return (
    <div className="margin-grid">
      {margin && <div className="margin-grid-margin">{margin}</div>}
      <div className="margin-grid-main">{children}</div>
      {aside && <div className="margin-grid-aside">{aside}</div>}
    </div>
  );
}

/** A page section. `mark` is a § number that sits in the margin and is hidden from assistive technology. */
export function Section({
  id,
  labelledBy,
  mark,
  aside,
  children,
}: {
  id?: string;
  labelledBy?: string;
  mark?: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={labelledBy} className="border-t py-16 first:border-t-0 md:py-24 lg:py-32" style={{ borderColor: "var(--rule-default)" }}>
      <Container>
        <MarginGrid margin={mark && <span aria-hidden className="t-section-mark">{mark}</span>} aside={aside}>
          {children}
        </MarginGrid>
      </Container>
    </section>
  );
}

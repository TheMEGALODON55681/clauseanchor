import { buildOffsetIndex, sliceCp } from "../../lib/offsets.ts";

/* The hero reads this fixture, not the mock adapter, so the landing page needs
   no session and no network call. Offsets are Unicode code points into the
   sample contract (api/contract.ts), the same ones the reader shows for the
   same findings. heroExamples.test.ts slices the contract with them. */

export type HeroExample = {
  category: string;
  status: "found" | "review";
  sectionPath: string;
  /** What this example shows, set in the margin. */
  caption: string;
  /** One paragraph of the contract, verbatim. */
  excerpt: string;
  excerptStart: number;
  start: number;
  end: number;
  quote: string;
};

export const HERO_EXAMPLES: HeroExample[] = [
  {
    category: "Non-Compete",
    status: "found",
    sectionPath: "Clause 4 › 4.1",
    caption: "Found. The marked words are the clause itself.",
    excerpt:
      "4.1 During the term of this Agreement and for a period of two (2) years after its termination or expiry, the Provider shall not, directly or indirectly, provide warehouse management or logistics services to any business that competes with the Company anywhere in India.",
    excerptStart: 2591,
    start: 2595,
    end: 2860,
    quote:
      "During the term of this Agreement and for a period of two (2) years after its termination or expiry, the Provider shall not, directly or indirectly, provide warehouse management or logistics services to any business that competes with the Company anywhere in India.",
  },
  {
    category: "Notice Period to Terminate Renewal",
    status: "found",
    sectionPath: "Clause 3 › 3.2",
    caption: "Found, and quoted word for word.",
    excerpt:
      '3.2 On expiry of the initial term, this Agreement shall automatically renew for successive periods of one (1) year each (each a "Renewal Term"), unless either Party gives the other written notice of non-renewal at least ninety (90) days before the end of the then current term.',
    excerptStart: 2296,
    start: 2441,
    end: 2572,
    quote: "unless either Party gives the other written notice of non-renewal at least ninety (90) days before the end of the then current term",
  },
  {
    category: "Competitive Restriction Exception",
    status: "review",
    sectionPath: "Clause 4 › 4.2",
    caption: "Needs a lawyer. The evidence is close, so ClauseAnchor shows the text and does not decide.",
    excerpt:
      "4.2 The restriction in Clause 4.1 shall not apply to services that the Provider was already providing to an existing client on the Effective Date and has disclosed in writing to the Company.",
    excerptStart: 2862,
    start: 2866,
    end: 3007,
    quote: "The restriction in Clause 4.1 shall not apply to services that the Provider was already providing to an existing client on the Effective Date",
  },
];

/** The excerpt in three parts around the finding. Offsets are code points, so the slice goes through offsets.ts. */
export function splitExcerpt(e: Pick<HeroExample, "excerpt" | "excerptStart" | "start" | "end">) {
  const index = buildOffsetIndex(e.excerpt);
  const from = e.start - e.excerptStart;
  const to = e.end - e.excerptStart;
  return {
    before: sliceCp(e.excerpt, index, 0, from),
    mark: sliceCp(e.excerpt, index, from, to),
    after: sliceCp(e.excerpt, index, to, index.cpLength),
  };
}

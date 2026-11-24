/* SA16 and the sample download (4-B.3, DY). One plain line for the landing page and /start: this is a public demo, so a visitor should
   bring a sample or a public contract. The agreement is fictional and sits in public/samples as a plain file, so the build needs no
   sample mode for it. The link is an in-sentence link, so it takes the prose style and a visited colour. */
export default function DemoNotice() {
  return (
    <p className="text-[15px] leading-[24px]" style={{ color: "var(--ink-secondary)" }}>
      This is a public demo. Use a sample or a public contract, not a confidential one.{" "}
      <a className="link-prose" href="/samples/fictional-services-agreement.docx" download>
        Download a fictional sample agreement<span className="sr-only"> (DOCX, 5 KB)</span>
      </a>
    </p>
  );
}

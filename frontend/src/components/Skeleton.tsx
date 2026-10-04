export type SkeletonVariant = "line" | "block" | "paragraph";

/* Slow shimmer over paper/sunken. Static under reduced-motion (see index.css). */
function Bar({ w, h }: { w: number | string; h: number }) {
  return (
    <div
      className="shimmer"
      style={{ width: w, height: h, borderRadius: 3, background: "var(--paper-sunken)" }}
    />
  );
}

export default function Skeleton({ variant = "line" }: { variant?: SkeletonVariant }) {
  if (variant === "block") {
    return <Bar w="100%" h={80} />;
  }
  if (variant === "paragraph") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%" }} aria-hidden>
        <Bar w="100%" h={12} />
        <Bar w="94%" h={12} />
        <Bar w="97%" h={12} />
        <Bar w="60%" h={12} />
      </div>
    );
  }
  return <Bar w={180} h={12} />;
}

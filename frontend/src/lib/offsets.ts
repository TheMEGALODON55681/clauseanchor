/* Backend offsets count Unicode code points. JavaScript strings index UTF-16
   code units. Build the table once per text and convert before every slice. */

export type OffsetIndex = {
  /** utf16[cp] is the UTF-16 index of code point cp. Length is cpLength + 1. */
  utf16: Uint32Array;
  cpLength: number;
};

export function buildOffsetIndex(text: string): OffsetIndex {
  const table: number[] = [];
  let i = 0;
  while (i < text.length) {
    table.push(i);
    const code = text.charCodeAt(i);
    const isHigh = code >= 0xd800 && code <= 0xdbff;
    const next = i + 1 < text.length ? text.charCodeAt(i + 1) : 0;
    i += isHigh && next >= 0xdc00 && next <= 0xdfff ? 2 : 1;
  }
  table.push(text.length);
  return { utf16: Uint32Array.from(table), cpLength: table.length - 1 };
}

export function toUtf16(index: OffsetIndex, cp: number): number {
  const clamped = Math.max(0, Math.min(cp, index.cpLength));
  return index.utf16[clamped];
}

/** Code point index for a UTF-16 index (binary search). */
export function toCodePoint(index: OffsetIndex, u16: number): number {
  let lo = 0;
  let hi = index.cpLength;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (index.utf16[mid] < u16) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function sliceCp(text: string, index: OffsetIndex, start: number, end: number): string {
  return text.slice(toUtf16(index, start), toUtf16(index, end));
}

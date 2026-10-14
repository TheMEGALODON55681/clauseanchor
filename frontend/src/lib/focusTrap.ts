const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

/* Keeps Tab and Shift+Tab inside `box`. A modal calls it from its key handler, so the header, the
   skip link and the rest of the page are out of reach by keyboard while it is open. */
export function trapTab(e: { key: string; shiftKey: boolean; preventDefault: () => void }, box: HTMLElement | null) {
  if (e.key !== "Tab" || !box) return;
  const items = [...box.querySelectorAll<HTMLElement>(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
  if (!items.length) {
    e.preventDefault();
    box.focus();
    return;
  }
  const now = document.activeElement;
  if (e.shiftKey && (now === items[0] || now === box)) {
    e.preventDefault();
    items[items.length - 1].focus();
  } else if (!e.shiftKey && now === items[items.length - 1]) {
    e.preventDefault();
    items[0].focus();
  }
}

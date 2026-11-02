const PATHS = {
  alert: '<path d="M12 3 2.8 20h18.4L12 3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  circle: '<circle cx="12" cy="12" r="7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  close: '<path d="m7 7 10 10M17 7 7 17"/>',
  draft: '<path d="M4 20h4L19 9l-4-4L4 16v4Z"/><path d="m13.5 6.5 4 4"/>',
  refresh: '<path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M6.1 8A7 7 0 0 1 18 6l2 6M18 16a7 7 0 0 1-11.9 2L4 12"/>',
};

export function icon(name, label = "") {
  const path = PATHS[name] ?? PATHS.circle;
  const safeLabel = String(label).replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
  const accessibility = label
    ? `role="img" aria-label="${safeLabel}"`
    : 'aria-hidden="true"';
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${accessibility}>${path}</svg>`;
}

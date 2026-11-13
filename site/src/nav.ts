/** Mobile menu: a full-screen overlay toggled from the nav. */
export function initNav() {
  const btn = document.getElementById("menu-btn");
  const menu = document.getElementById("menu");
  if (!btn || !menu) return;
  const set = (open: boolean) => {
    btn.setAttribute("aria-expanded", String(open));
    btn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    document.body.classList.toggle("menu-open", open);
    if (open) menu.hidden = false;
    else setTimeout(() => (menu.hidden = !document.body.classList.contains("menu-open") ? true : menu.hidden), 500);
  };
  btn.addEventListener("click", () => set(btn.getAttribute("aria-expanded") !== "true"));
  menu.addEventListener("click", (e) => {
    if ((e.target as HTMLElement).closest("a")) set(false);
  });
  document.addEventListener("keydown", (e) => e.key === "Escape" && set(false));
  document.addEventListener("plexa:navigate", () => set(false));
}

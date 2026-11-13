/** Contact form: composes a pre-filled GitHub issue (no backend, nothing stored by us). */
export function initContact() {
  const form = document.getElementById("contact-form") as HTMLFormElement | null;
  if (!form) return;
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const get = (k: string) => String(data.get(k) ?? "").trim();
    const title = `[${get("topic")}] ${get("message").split("\n")[0]!.slice(0, 70)}`;
    const body = [`**From:** ${get("name")}${get("org") ? ` (${get("org")})` : ""}`, `**Topic:** ${get("topic")}`, "", get("message")].join("\n");
    const url = `https://github.com/plexahq/plexahq/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
    window.open(url, "_blank", "noopener");
  });
}

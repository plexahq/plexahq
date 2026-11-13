/** Contact form: posts to /api/contact, which stores the message privately in Vercel Blob. */
export function initContact() {
  const form = document.getElementById("contact-form") as HTMLFormElement | null;
  const status = document.getElementById("form-status");
  if (!form || !status) return;
  const button = form.querySelector<HTMLButtonElement>("button[type=submit]")!;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    button.disabled = true;
    status.className = "form-note";
    status.textContent = "Sending…";
    try {
      const res = await fetch("/api/contact", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });
      const body = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) throw new Error(body.error ?? "Something went wrong. Please try again.");
      form.reset();
      status.className = "form-note ok";
      status.textContent = "Thanks, your message reached the team. We'll reply by email.";
    } catch (err) {
      status.className = "form-note err";
      status.textContent = (err as Error).message;
    } finally {
      button.disabled = false;
    }
  });
}

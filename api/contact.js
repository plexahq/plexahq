// Vercel function for the website's contact form.
// Messages are stored as private JSON files in Vercel Blob (contact/YYYY-MM-DD/...); only the team can read them.
import { put } from "@vercel/blob";

const json = (status, body) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

const clean = (v, max) => String(v ?? "").replace(/[\u0000-\u0008\u000b-\u001f]/g, "").trim().slice(0, max);

export async function POST(request) {
  if (Number(request.headers.get("content-length") ?? 0) > 20000) return json(413, { error: "Message too long." });
  let body;
  try {
    body = await request.json();
  } catch {
    return json(400, { error: "Invalid request." });
  }
  // honeypot: real people never fill the hidden "website" field
  if (clean(body.website, 200)) return json(200, { ok: true });
  const msg = {
    at: new Date().toISOString(),
    name: clean(body.name, 80),
    email: clean(body.email, 120),
    org: clean(body.org, 80),
    topic: clean(body.topic, 40),
    message: clean(body.message, 4000),
  };
  if (!msg.name || !msg.message || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(msg.email)) {
    return json(400, { error: "Please add your name, a valid email and a message." });
  }
  if (!process.env.BLOB_READ_WRITE_TOKEN) return json(503, { error: "Messages can't be received right now. Please try again later." });
  try {
    await put(`contact/${msg.at.slice(0, 10)}/${msg.at.replace(/[:.]/g, "-")}.json`, JSON.stringify(msg, null, 2), {
      access: "private",
      contentType: "application/json",
      addRandomSuffix: true,
    });
  } catch (error) {
    console.error("contact: storing message failed", error);
    return json(502, { error: "Your message couldn't be saved. Please try again in a moment." });
  }
  return json(200, { ok: true });
}

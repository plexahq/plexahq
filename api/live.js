// Vercel function for /api/live: the website's live feed (cached at the CDN, see src/web.ts).
import { handleLive } from "../dist/web.js";

export function GET(request) {
  return handleLive(new URL(request.url));
}

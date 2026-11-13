// Vercel function for /health (rewritten here in vercel.json).
import { handleHealth } from "../dist/web.js";

export function GET() {
  return handleHealth();
}

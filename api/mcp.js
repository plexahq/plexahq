// Vercel function for the MCP endpoint (/mcp is rewritten here in vercel.json).
// It runs the compiled server from dist/, produced by `npm run build` during the Vercel build.
import { handleMcpRequest } from "../dist/web.js";

export function GET(request) {
  return handleMcpRequest(request);
}

export function POST(request) {
  return handleMcpRequest(request);
}

export function OPTIONS(request) {
  return handleMcpRequest(request);
}

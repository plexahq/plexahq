import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";
import { Readable } from "node:stream";
import { VERSION } from "./server.js";
import { CORS_HEADERS, handleHealth, handleMcpRequest } from "./web.js";

/**
 * Standalone Node HTTP server (for Docker, Railway, Fly.io, a VPS or local use).
 * On Vercel the same handler runs as a serverless function from api/.
 */

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";

function toRequest(req: IncomingMessage): Request {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (Array.isArray(value)) value.forEach((v) => headers.append(key, v));
    else if (value !== undefined) headers.set(key, value);
  }
  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  return new Request(url, {
    method: req.method,
    headers,
    body: hasBody ? (Readable.toWeb(req) as ReadableStream) : undefined,
    duplex: "half",
  } as RequestInit);
}

async function send(res: ServerResponse, response: Response): Promise<void> {
  res.writeHead(response.status, Object.fromEntries(response.headers));
  if (response.body) {
    for await (const chunk of response.body) res.write(chunk);
  }
  res.end();
}

const httpServer = createHttpServer(async (req, res) => {
  try {
    const { pathname } = new URL(req.url ?? "/", "http://localhost");
    let response: Response;
    if (pathname === "/health") response = handleHealth();
    else if (pathname === "/mcp") response = await handleMcpRequest(toRequest(req));
    else {
      response = new Response(JSON.stringify({ error: "Not found. The MCP endpoint is /mcp" }), {
        status: 404,
        headers: { "content-type": "application/json", ...CORS_HEADERS },
      });
    }
    await send(res, response);
  } catch (error) {
    console.error("Request failed:", error);
    if (!res.headersSent) res.writeHead(500, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: "Internal server error" }));
  }
});

httpServer.listen(PORT, HOST, () => {
  console.error(`Plexa MCP ${VERSION} listening on http://${HOST}:${PORT}/mcp`);
});

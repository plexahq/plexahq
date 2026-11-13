import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "./src/server.js";
const client = new Client({ name: "t", version: "0" });
const [a, b] = InMemoryTransport.createLinkedPair();
await createServer().connect(b); await client.connect(a);
const call = async (name: string, args: Record<string, unknown>) => {
  const t = Date.now();
  const r = (await client.callTool({ name, arguments: args })) as { isError?: boolean; content: { text: string }[] };
  console.log(`\n=== ${name} ${JSON.stringify(args)} (${Date.now() - t}ms) ${r.isError ? "ERROR" : ""}`);
  const txt = r.content[0]!.text; console.log(process.env.TAIL ? txt.slice(-1400) : txt.slice(0, 2600));
};
const which = process.argv[2] ?? "all";
if (which === "all" || which === "sec") {
  await call("lz_app_security", { chain: "ethereum", address: "0x6985884C4392D348587B19cb9eAAf157F13271cd" });
  await call("lz_app_security", { chain: "ethereum", address: "0x6C96dE32CEa08842dcc4058c14d3aaAD7Fa41dee", maxPathways: 3 });
}
if (which === "all" || which === "zro") await call("zro_overview", { address: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" });
if (which === "all" || which === "stocks") {
  await call("stocks_lookup", { query: "NVDA" });
  await call("stocks_lookup", { query: "s&p 500" });
  await call("stocks_portfolio", { address: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045" });
}
await client.close();

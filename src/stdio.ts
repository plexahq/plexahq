#!/usr/bin/env node
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer, VERSION } from "./server.js";

// stdout carries the MCP protocol; log only to stderr.
const server = createServer();
await server.connect(new StdioServerTransport());
console.error(`Plexa MCP ${VERSION} running on stdio`);

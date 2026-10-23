"use strict";

const http = require("node:http");

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8000;
const BRIDGE_HOST = "127.0.0.1";
const BRIDGE_PORT = 8765;
const WEBHOOK_PATH = "/api/alexa/skill";
const MAX_BODY_BYTES = 1024 * 1024;

const server = http.createServer((request, response) => {
  if (request.method !== "POST" || request.url !== WEBHOOK_PATH) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not Found");
    return;
  }

  const contentLength = Number(request.headers["content-length"] || 0);
  if (contentLength > MAX_BODY_BYTES) {
    request.resume();
    response.writeHead(413, { "content-type": "text/plain; charset=utf-8" });
    response.end("Request too large");
    return;
  }

  const headers = {
    host: `${BACKEND_HOST}:${BACKEND_PORT}`,
    "content-type": request.headers["content-type"] || "application/json",
  };
  for (const name of ["signaturecertchainurl", "signature-256", "signature"]) {
    if (request.headers[name]) headers[name] = request.headers[name];
  }
  if (request.headers["content-length"]) {
    headers["content-length"] = request.headers["content-length"];
  }

  const upstream = http.request(
    {
      host: BACKEND_HOST,
      port: BACKEND_PORT,
      method: "POST",
      path: WEBHOOK_PATH,
      headers,
      timeout: 15000,
    },
    (upstreamResponse) => {
      response.writeHead(upstreamResponse.statusCode || 502, {
        "content-type": upstreamResponse.headers["content-type"] || "application/json",
      });
      upstreamResponse.pipe(response);
    },
  );

  let bodyBytes = 0;
  request.on("data", (chunk) => {
    bodyBytes += chunk.length;
    if (bodyBytes > MAX_BODY_BYTES) {
      upstream.destroy();
      if (!response.headersSent) {
        response.writeHead(413, { "content-type": "text/plain; charset=utf-8" });
      }
      response.end("Request too large");
    }
  });
  request.on("error", () => upstream.destroy());
  upstream.on("timeout", () => upstream.destroy(new Error("Backend request timed out")));
  upstream.on("error", () => {
    if (response.headersSent) return;
    response.writeHead(502, { "content-type": "text/plain; charset=utf-8" });
    response.end("Backend unavailable");
  });
  request.pipe(upstream);
});

server.listen(BRIDGE_PORT, BRIDGE_HOST, () => {
  console.log(`Alexa-only bridge listening on http://${BRIDGE_HOST}:${BRIDGE_PORT}`);
});

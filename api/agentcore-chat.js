const crypto = require("crypto");
const { routeChatEvent } = require("./_agentcore/fast-router");
const { loadVersionRegistry } = require("./_agentcore/version");

function logRouterEvent(label, details = {}) {
  console.log(
    JSON.stringify({
      service: "agentcore-chat",
      label,
      at: new Date().toISOString(),
      ...details,
    })
  );
}

async function readJsonBody(request) {
  if (request.body && typeof request.body === "object") {
    return request.body;
  }
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

function base64UrlDecode(value) {
  const padded = `${value}${"=".repeat((4 - (value.length % 4)) % 4)}`;
  return Buffer.from(padded.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

async function googleCertForKid(kid) {
  const response = await fetch("https://www.googleapis.com/oauth2/v3/certs");
  if (!response.ok) {
    throw new Error(`Unable to fetch Google OIDC certs: ${response.status}`);
  }
  const payload = await response.json();
  const key = (payload.keys || []).find((candidate) => candidate.kid === kid);
  if (!key) {
    throw new Error(`No Google OIDC cert found for kid ${kid}`);
  }
  return crypto.createPublicKey({ key, format: "jwk" });
}

function expectedAudience(request) {
  if (process.env.AGENTCORE_CHAT_AUDIENCE) {
    return process.env.AGENTCORE_CHAT_AUDIENCE;
  }
  const proto = request.headers["x-forwarded-proto"] || "https";
  const host = request.headers["x-forwarded-host"] || request.headers.host;
  return `${proto}://${host}${request.url.split("?")[0]}`;
}

async function verifyGoogleChatRequest(request) {
  if (process.env.AGENTCORE_CHAT_VERIFY_AUTH === "false") {
    return;
  }
  const auth = request.headers.authorization || request.headers.Authorization || "";
  const token = auth.startsWith("Bearer ") ? auth.slice("Bearer ".length) : "";
  if (!token) {
    throw new Error("Missing Google Chat bearer token.");
  }
  const [encodedHeader, encodedPayload, encodedSignature] = token.split(".");
  if (!encodedHeader || !encodedPayload || !encodedSignature) {
    throw new Error("Invalid bearer token format.");
  }
  const header = JSON.parse(base64UrlDecode(encodedHeader).toString("utf8"));
  const payload = JSON.parse(base64UrlDecode(encodedPayload).toString("utf8"));
  if (header.alg !== "RS256") {
    throw new Error(`Unexpected token algorithm: ${header.alg}`);
  }
  const publicKey = await googleCertForKid(header.kid);
  const verifier = crypto.createVerify("RSA-SHA256");
  verifier.update(`${encodedHeader}.${encodedPayload}`);
  verifier.end();
  const ok = verifier.verify(publicKey, base64UrlDecode(encodedSignature));
  if (!ok) {
    throw new Error("Google Chat bearer token signature failed verification.");
  }
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) {
    throw new Error("Google Chat bearer token is expired.");
  }
  const issuerOk = payload.iss === "https://accounts.google.com" || payload.iss === "accounts.google.com";
  if (!issuerOk) {
    throw new Error(`Unexpected token issuer: ${payload.iss}`);
  }
  if (payload.aud !== expectedAudience(request)) {
    throw new Error("Google Chat bearer token audience does not match endpoint URL.");
  }
  if (payload.email && payload.email !== "chat@system.gserviceaccount.com") {
    throw new Error(`Unexpected token email: ${payload.email}`);
  }
}

module.exports = async function handler(request, response) {
  if (request.method === "GET") {
    logRouterEvent("health_check", { method: request.method });
    const registry = loadVersionRegistry();
    response.status(200).json({
      status: "ok",
      service: "agentcore-chat",
      fast_model: process.env.AGENTCORE_FAST_MODEL || "gemini-2.5-flash",
      router_version: registry.router_version,
      context_bundle_version: registry.context_bundle_version,
    });
    return;
  }
  if (request.method !== "POST") {
    logRouterEvent("method_not_allowed", { method: request.method });
    response.setHeader("Allow", "GET, POST");
    response.status(405).json({ error: "method_not_allowed" });
    return;
  }
  try {
    await verifyGoogleChatRequest(request);
    const event = await readJsonBody(request);
    const text = String((event.message && (event.message.argumentText || event.message.text)) || event.text || "");
    logRouterEvent("chat_event_received", {
      event_type: event.type || "",
      space: (event.space && event.space.name) || (event.message && event.message.space && event.message.space.name) || "",
      sender: (event.user && (event.user.displayName || event.user.name || event.user.email)) || "",
      text_preview: text.slice(0, 120),
    });
    const routed = await routeChatEvent(event);
    logRouterEvent("chat_event_routed", routed._meta || {});
    response.status(200).json({ text: routed.text || "Got it." });
  } catch (error) {
    const expose = process.env.AGENTCORE_ROUTER_DEBUG === "true";
    const message = String(error && error.message ? error.message : error);
    const status = /token|authorization|audience|issuer|signature|bearer/i.test(message) ? 401 : 500;
    logRouterEvent("chat_event_error", { status, message: message.slice(0, 300) });
    response.status(status).json({
      text: "I hit a snag in the fast responder. I’ll need the deeper agent to fix the endpoint.",
      error: expose ? String(error && error.stack ? error.stack : error) : "fast_router_error",
    });
  }
};

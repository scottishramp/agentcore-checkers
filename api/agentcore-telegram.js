const { loadFastContext } = require("./_agentcore/context");
const { historyConfigured, historyMessageLimit, historyTtlSeconds } = require("./_agentcore/store");
const { loadVersionRegistry } = require("./_agentcore/version");
const { routeChatEvent } = require("./_agentcore/fast-router");
const {
  allowedUserIds,
  botToken,
  isUserAllowed,
  sendTelegramMessage,
  updateToEvent,
} = require("./_agentcore/telegram");

function logRouterEvent(label, details = {}) {
  console.log(
    JSON.stringify({
      service: "agentcore-telegram",
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

function scheduleBackground(work) {
  try {
    const { waitUntil } = require("@vercel/functions");
    if (typeof waitUntil === "function") {
      waitUntil(work);
      return;
    }
  } catch (_error) {
    // Local tests and non-Vercel runtimes just finish the work in-process.
  }
  return work;
}

async function routeAndReply(event) {
  const loaded = await loadFastContext();
  const routed = await routeChatEvent(event, { context: loaded.context });
  try {
    await sendTelegramMessage(event.agentcore.telegram_chat_id, routed.text || "Got it.");
  } catch (sendError) {
    logRouterEvent("telegram_send_error", {
      message: String(sendError && sendError.message ? sendError.message : sendError).slice(0, 300),
    });
  }
  logRouterEvent("telegram_message_routed", routed._meta || {});
}

function verifyWebhookSecret(request) {
  const expected = process.env.AGENTCORE_TELEGRAM_WEBHOOK_SECRET || "";
  if (!expected) {
    return;
  }
  const provided =
    request.headers["x-telegram-bot-api-secret-token"] ||
    request.headers["X-Telegram-Bot-Api-Secret-Token"] ||
    "";
  if (provided !== expected) {
    throw new Error("Invalid Telegram webhook secret.");
  }
}

module.exports = async function handler(request, response) {
  if (request.method === "GET") {
    logRouterEvent("health_check", { configured: Boolean(botToken()) });
    const registry = loadVersionRegistry();
    const snapshot = await loadFastContext();
    response.status(200).json({
      status: "ok",
      service: "agentcore-telegram",
      fast_model: process.env.AGENTCORE_FAST_MODEL || "gemini-3.7-flash",
      bot_configured: Boolean(botToken()),
      allowlist_count: allowedUserIds().length,
      history_configured: historyConfigured(),
      history_message_limit: historyMessageLimit(),
      history_persistent: historyTtlSeconds() === 0,
      router_version: registry.router_version,
      context_bundle_version: registry.context_bundle_version,
      context_source: snapshot.source,
      context_published_at: snapshot.published_at || "",
      context_hash: snapshot.context_hash,
      context_length: snapshot.context_length,
      context_files: snapshot.context_files,
      has_nathan_birthdate: snapshot.has_nathan_birthdate,
    });
    return;
  }
  if (request.method !== "POST") {
    response.setHeader("Allow", "GET, POST");
    response.status(405).json({ error: "method_not_allowed" });
    return;
  }

  try {
    verifyWebhookSecret(request);
    const update = await readJsonBody(request);
    const event = updateToEvent(update);
    if (!event) {
      logRouterEvent("ignored_update", { update_id: update && update.update_id });
      response.status(200).json({ ok: true, ignored: true });
      return;
    }

    const userId = event.agentcore.telegram_user_id;
    if (!isUserAllowed(userId)) {
      logRouterEvent("user_not_allowed", {
        user_id: userId,
        username: event.agentcore.telegram_username,
      });
      response.status(200).json({ ok: true, ignored: true, allowed: false });
      return;
    }

    logRouterEvent("telegram_message_received", {
      user_id: userId,
      username: event.agentcore.telegram_username,
      text_preview: event.message.text.slice(0, 120),
      has_media: Boolean(event.agentcore.media),
    });

    const work = routeAndReply(event).catch((error) => {
      logRouterEvent("telegram_background_error", {
        message: String(error && error.message ? error.message : error).slice(0, 300),
        has_media: Boolean(event.agentcore.media),
      });
    });

    // Photos: ack Telegram immediately so the webhook cannot 504, then let Gemini
    // use the rest of the function lifetime (up to maxDuration).
    if (event.agentcore.media) {
      const scheduled = scheduleBackground(work);
      response.status(200).json({ ok: true, accepted: true });
      if (scheduled && typeof scheduled.then === "function") {
        await scheduled;
      }
      return;
    }

    await work;
    response.status(200).json({ ok: true });
  } catch (error) {
    const message = String(error && error.message ? error.message : error);
    const status = /secret|token|authorization/i.test(message) ? 401 : 500;
    logRouterEvent("telegram_error", { status, message: message.slice(0, 300) });
    response.status(status).json({
      ok: false,
      error: process.env.AGENTCORE_ROUTER_DEBUG === "true" ? message : "telegram_router_error",
    });
  }
};

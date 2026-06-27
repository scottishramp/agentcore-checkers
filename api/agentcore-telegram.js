const { buildContext } = require("./_agentcore/context");
const { routeChatEvent } = require("./_agentcore/fast-router");
const {
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
    response.status(200).json({
      status: "ok",
      service: "agentcore-telegram",
      fast_model: process.env.AGENTCORE_FAST_MODEL || "gemini-2.5-flash",
      bot_configured: Boolean(botToken()),
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
      logRouterEvent("user_not_allowed", { user_id: userId });
      await sendTelegramMessage(
        event.agentcore.telegram_chat_id,
        "This bot is private. Ask Brian to add your Telegram user id to the allowlist.",
      );
      response.status(200).json({ ok: true, allowed: false });
      return;
    }

    logRouterEvent("telegram_message_received", {
      user_id: userId,
      username: event.agentcore.telegram_username,
      text_preview: event.message.text.slice(0, 120),
    });

    const routed = await routeChatEvent(event, { context: buildContext() });
    await sendTelegramMessage(event.agentcore.telegram_chat_id, routed.text || "Got it.");
    logRouterEvent("telegram_message_routed", routed._meta || {});
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

function botToken(env = process.env) {
  return env.TELEGRAM_BOT_TOKEN || env.AGENTCORE_TELEGRAM_BOT_TOKEN || "";
}

function allowedUserIds(env = process.env) {
  const raw = env.AGENTCORE_TELEGRAM_ALLOWED_USER_IDS || "";
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function isUserAllowed(userId, env = process.env) {
  const allowed = allowedUserIds(env);
  if (!allowed.length) {
    return true;
  }
  return allowed.includes(String(userId));
}

function displayName(from = {}) {
  const parts = [from.first_name, from.last_name].filter(Boolean);
  if (parts.length) {
    return parts.join(" ");
  }
  if (from.username) {
    return `@${from.username}`;
  }
  return `telegram:${from.id || "unknown"}`;
}

function updateToEvent(update) {
  const message = update && update.message ? update.message : null;
  if (!message || !message.text) {
    return null;
  }
  const from = message.from || {};
  const chat = message.chat || {};
  const userId = String(from.id || "");
  const chatId = String(chat.id || "");
  const updateId = String(update.update_id || message.message_id || "");
  const conversationKey = `telegram:dm:${chatId}`;
  return {
    type: "MESSAGE",
    user: {
      name: `telegram:${userId}`,
      displayName: displayName(from),
      email: "",
    },
    space: { name: conversationKey },
    message: {
      name: `telegram:${updateId}`,
      text: String(message.text || "").trim(),
      thread: { name: `${conversationKey}/thread` },
    },
    agentcore: {
      source_kind: "telegram",
      message_id: `telegram:${updateId}`,
      conversation_id: conversationKey,
      sender_id: `telegram:${userId}`,
      sender_display_name: displayName(from),
      telegram_chat_id: chatId,
      telegram_user_id: userId,
      telegram_username: String(from.username || ""),
      conversation_key: conversationKey,
    },
  };
}

async function sendTelegramMessage(chatId, text, env = process.env) {
  const token = botToken(env);
  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: String(text || "Got it."),
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(`Telegram sendMessage failed: ${response.status} ${JSON.stringify(payload).slice(0, 500)}`);
  }
  return payload.result || {};
}

async function setWebhook(webhookUrl, env = process.env) {
  const token = botToken(env);
  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }
  const secret = env.AGENTCORE_TELEGRAM_WEBHOOK_SECRET || "";
  const body = { url: webhookUrl, drop_pending_updates: true };
  if (secret) {
    body.secret_token = secret;
  }
  const response = await fetch(`https://api.telegram.org/bot${token}/setWebhook`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(`Telegram setWebhook failed: ${response.status} ${JSON.stringify(payload).slice(0, 500)}`);
  }
  return payload;
}

async function getWebhookInfo(env = process.env) {
  const token = botToken(env);
  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }
  const response = await fetch(`https://api.telegram.org/bot${token}/getWebhookInfo`);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(`Telegram getWebhookInfo failed: ${response.status} ${JSON.stringify(payload).slice(0, 500)}`);
  }
  return payload.result || {};
}

module.exports = {
  allowedUserIds,
  botToken,
  displayName,
  getWebhookInfo,
  isUserAllowed,
  sendTelegramMessage,
  setWebhook,
  updateToEvent,
};

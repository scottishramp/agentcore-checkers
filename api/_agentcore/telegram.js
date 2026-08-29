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
    return false;
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

function compactWhitespace(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function pickLargestPhoto(photos) {
  if (!Array.isArray(photos) || !photos.length) {
    return null;
  }
  return photos.reduce((best, candidate) => {
    const bestSize = Number((best && best.file_size) || 0);
    const candidateSize = Number((candidate && candidate.file_size) || 0);
    if (!best) {
      return candidate;
    }
    if (candidateSize > bestSize) {
      return candidate;
    }
    if (candidateSize === bestSize && Number(candidate.width || 0) > Number(best.width || 0)) {
      return candidate;
    }
    return best;
  }, null);
}

function mimeFromFilePath(filePath) {
  const lower = String(filePath || "").toLowerCase();
  if (lower.endsWith(".png")) {
    return "image/png";
  }
  if (lower.endsWith(".webp")) {
    return "image/webp";
  }
  if (lower.endsWith(".gif")) {
    return "image/gif";
  }
  return "image/jpeg";
}

function extractMedia(message) {
  if (!message || typeof message !== "object") {
    return null;
  }
  const photo = pickLargestPhoto(message.photo);
  if (photo && photo.file_id) {
    return {
      type: "photo",
      telegram_file_id: String(photo.file_id),
      telegram_file_unique_id: String(photo.file_unique_id || ""),
      mime_type: "image/jpeg",
      file_size: Number(photo.file_size || 0),
      width: Number(photo.width || 0),
      height: Number(photo.height || 0),
    };
  }
  const document = message.document || null;
  if (document && document.file_id && String(document.mime_type || "").startsWith("image/")) {
    return {
      type: "document_image",
      telegram_file_id: String(document.file_id),
      telegram_file_unique_id: String(document.file_unique_id || ""),
      mime_type: String(document.mime_type || "image/jpeg"),
      file_size: Number(document.file_size || 0),
      file_name: String(document.file_name || ""),
    };
  }
  return null;
}

function messageContent(message) {
  const text = compactWhitespace(message && message.text);
  const caption = compactWhitespace(message && message.caption);
  const media = extractMedia(message);
  const body = text || caption;
  if (!body && !media) {
    return null;
  }
  return {
    text: body || (media ? "[photo attached]" : ""),
    media,
  };
}

function updateToEvent(update) {
  const message = update && update.message ? update.message : null;
  const content = messageContent(message);
  if (!content) {
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
      text: content.text,
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
      media: content.media || null,
    },
  };
}

function fetchTimeoutMs(env = process.env, fallback = 8000) {
  const raw = Number(env.AGENTCORE_TELEGRAM_FETCH_TIMEOUT_MS || fallback);
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

function abortSignal(ms) {
  return typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
    ? AbortSignal.timeout(ms)
    : undefined;
}

async function downloadTelegramFile(fileId, env = process.env) {
  const token = botToken(env);
  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }
  const maxBytes = Number(env.AGENTCORE_TELEGRAM_MAX_DOWNLOAD_BYTES || 4 * 1024 * 1024);
  const timeoutMs = fetchTimeoutMs(env, 15000);
  const metaResponse = await fetch(
    `https://api.telegram.org/bot${token}/getFile?file_id=${encodeURIComponent(String(fileId || ""))}`,
    { signal: abortSignal(timeoutMs) },
  );
  const metaPayload = await metaResponse.json().catch(() => ({}));
  if (!metaResponse.ok || !metaPayload.ok || !metaPayload.result || !metaPayload.result.file_path) {
    throw new Error(`Telegram getFile failed: ${metaResponse.status} ${JSON.stringify(metaPayload).slice(0, 300)}`);
  }
  const filePath = String(metaPayload.result.file_path);
  const fileSize = Number(metaPayload.result.file_size || 0);
  if (fileSize > maxBytes) {
    throw new Error(`Telegram file exceeds download limit (${fileSize} > ${maxBytes}).`);
  }
  const fileResponse = await fetch(`https://api.telegram.org/file/bot${token}/${filePath}`, {
    signal: abortSignal(timeoutMs),
  });
  if (!fileResponse.ok) {
    throw new Error(`Telegram file download failed: ${fileResponse.status}`);
  }
  const arrayBuffer = await fileResponse.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);
  if (buffer.length > maxBytes) {
    throw new Error(`Telegram file exceeds download limit (${buffer.length} > ${maxBytes}).`);
  }
  return {
    buffer,
    mime_type: mimeFromFilePath(filePath),
    file_path: filePath,
    file_size: buffer.length,
  };
}

async function sendTelegramMessage(chatId, text, env = process.env) {
  const token = botToken(env);
  if (!token) {
    throw new Error("Missing TELEGRAM_BOT_TOKEN.");
  }
  const clipped = String(text || "Got it.");
  const limit = 4000;
  const bodyText = clipped.length > limit ? `${clipped.slice(0, limit - 14)}\n…[truncated]` : clipped;
  const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: bodyText,
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
  downloadTelegramFile,
  extractMedia,
  getWebhookInfo,
  isUserAllowed,
  messageContent,
  sendTelegramMessage,
  setWebhook,
  updateToEvent,
};

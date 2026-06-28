const crypto = require("crypto");

function hashKey(value) {
  return crypto.createHash("sha256").update(String(value || "unknown")).digest("hex").slice(0, 32);
}

function redisConfig(env = process.env) {
  const url = env.UPSTASH_REDIS_REST_URL || env.KV_REST_API_URL || "";
  const token = env.UPSTASH_REDIS_REST_TOKEN || env.KV_REST_API_TOKEN || "";
  return { url: url.replace(/\/+$/, ""), token };
}

async function redisCommand(command, env = process.env) {
  const { url, token } = redisConfig(env);
  if (!url || !token) {
    return { configured: false, result: null };
  }
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(command),
  });
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`Upstash returned non-JSON response: ${text.slice(0, 200)}`);
  }
  if (!response.ok) {
    throw new Error(`Upstash command failed: ${response.status} ${JSON.stringify(payload).slice(0, 300)}`);
  }
  return { configured: true, result: payload.result };
}

async function getHistory(conversationKey, env = process.env) {
  const key = `agentcore:router:${hashKey(conversationKey)}`;
  const { configured, result } = await redisCommand(["GET", key], env);
  if (!configured || !result) {
    return [];
  }
  try {
    const parsed = JSON.parse(result);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function historyMessageLimit(env = process.env) {
  const explicit = Number(env.AGENTCORE_FAST_HISTORY_MESSAGES);
  if (Number.isFinite(explicit) && explicit > 0) {
    return Math.floor(explicit);
  }
  const turns = Number(env.AGENTCORE_FAST_HISTORY_TURNS || 10);
  return Math.floor(turns * 2);
}

function historyTtlSeconds(env = process.env) {
  const raw = env.AGENTCORE_FAST_HISTORY_TTL_SECONDS;
  if (raw === "0" || raw === "false" || raw === "none" || raw === "off") {
    return 0;
  }
  if (raw !== undefined && String(raw).trim() !== "") {
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : 0;
  }
  return 0;
}

async function saveHistory(conversationKey, history, env = process.env) {
  const key = `agentcore:router:${hashKey(conversationKey)}`;
  const limit = historyMessageLimit(env);
  const ttlSeconds = historyTtlSeconds(env);
  const trimmed = history.slice(Math.max(0, history.length - limit));
  const command =
    ttlSeconds > 0
      ? ["SET", key, JSON.stringify(trimmed), "EX", String(ttlSeconds)]
      : ["SET", key, JSON.stringify(trimmed)];
  return redisCommand(command, env);
}

function historyConfigured(env = process.env) {
  const { url, token } = redisConfig(env);
  return Boolean(url && token);
}

module.exports = {
  getHistory,
  saveHistory,
  redisCommand,
  historyConfigured,
  historyMessageLimit,
  historyTtlSeconds,
};

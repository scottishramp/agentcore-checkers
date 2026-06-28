const { buildContext, runtimeClock, tryDeterministicFoodAnswer } = require("./context");
const { enqueueTelegramMessage } = require("./inbox-queue");
const { getHistory, saveHistory } = require("./store");
const { loadVersionRegistry, tryDeterministicVersionAnswer, versionMetadata } = require("./version");

const DEFAULT_MODEL = "gemini-2.5-flash";

function compactWhitespace(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function extractMessageText(event) {
  const message = event && event.message ? event.message : {};
  return compactWhitespace(message.argumentText || message.text || event.text || "");
}

function conversationKeyForEvent(event) {
  const message = event && event.message ? event.message : {};
  const threadName = message.thread && message.thread.name;
  const spaceName = (event.space && event.space.name) || message.space && message.space.name;
  const userName = event.user && event.user.name;
  return threadName || spaceName || userName || "unknown";
}

function senderForEvent(event) {
  const user = event && event.user ? event.user : {};
  const messageSender = event && event.message && event.message.sender ? event.message.sender : {};
  return {
    name: user.name || messageSender.name || "",
    displayName: user.displayName || messageSender.displayName || "",
    email: user.email || messageSender.email || "",
  };
}

function chatMessageName(event) {
  return event && event.message && event.message.name ? event.message.name : "";
}

function chatSpaceName(event) {
  return event && event.space && event.space.name
    ? event.space.name
    : event && event.message && event.message.space && event.message.space.name
      ? event.message.space.name
      : "";
}

function fallbackDecision(text) {
  const lowered = text.toLowerCase();
  if (!text) {
    return {
      route: "lightweight_answer",
      response: "I did not receive any message text.",
      confidence: 0.4,
    };
  }
  if (/^(hi|hello|hey|test|ping)\b/.test(lowered)) {
    return {
      route: "lightweight_answer",
      response: "I’m here. I can answer quick questions here, and I’ll hand deeper tasks off to the repo-backed Cursor agent.",
      confidence: 0.55,
    };
  }
  if (/\b(ate|breakfast|lunch|dinner|snack|food|journal|address|phone|birthday|remember|note)\b/.test(lowered)) {
    return {
      route: "knowledge_update",
      response: "Got it. I’ll remember this here for the conversation and queue it for durable filing in the knowledge base.",
      async_task_title: "Ingest personal update from Telegram",
      async_task_body: text,
      confidence: 0.5,
    };
  }
  return {
    route: "task",
    response: "Got it. I’ll hand this to the repo-backed Cursor agent for a deeper pass.",
    async_task_title: "Handle Telegram task",
    async_task_body: text,
    confidence: 0.45,
  };
}

function parseJsonFromText(text) {
  const raw = String(text || "").trim();
  if (!raw) {
    throw new Error("Empty model response.");
  }
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1].trim() : raw;
  const firstBrace = candidate.indexOf("{");
  const lastBrace = candidate.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    return JSON.parse(candidate.slice(firstBrace, lastBrace + 1));
  }
  return JSON.parse(candidate);
}

function normalizeDecision(decision, fallbackText) {
  const allowed = new Set(["lightweight_answer", "knowledge_update", "task", "needs_clarification", "ignore"]);
  const route = allowed.has(decision.route) ? decision.route : "task";
  const response = compactWhitespace(decision.response) || fallbackDecision(fallbackText).response;
  const rawConfidence = Number(decision.confidence || 0);
  const confidence = rawConfidence > 1 ? rawConfidence / 10 : rawConfidence;
  return {
    route,
    response,
    async_task_title: compactWhitespace(decision.async_task_title) || "",
    async_task_body: String(decision.async_task_body || fallbackText).trim(),
    confidence: Math.max(0, Math.min(1, confidence || 0)),
  };
}

function geminiApiKey(env = process.env) {
  return env.GOOGLE_AI_STUDIO_API_KEY || env.GEMINI_API_KEY || env.GOOGLE_API_KEY || "";
}

async function callGemini({ text, context, history, sender, env = process.env }) {
  const apiKey = geminiApiKey(env);
  if (!apiKey) {
    return fallbackDecision(text);
  }
  const model = env.AGENTCORE_FAST_MODEL || DEFAULT_MODEL;
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const clock = runtimeClock(env);
  const registry = loadVersionRegistry();
  const versionLine = `Chatbot version: ${registry.name} v${registry.router_version} (context v${registry.context_bundle_version}, released ${registry.released_at || "unknown"}).`;
  const system = [
    "You are AgentCore's fast Telegram chat assistant for Brian Herbert and family.",
    versionLine,
    `Authoritative runtime clock: ${clock.localDisplay} (${clock.timezone}). Local date: ${clock.localDate}. Use this for today/yesterday; never guess the date.`,
    "Answer ONLY from the compact repo context below. If the context lacks the fact, say you do not have it yet — never invent meals, dates, or personal details.",
    "The food log is in agentcore/knowledge/people/brian-herbert-food-log.md under ## YYYY-MM-DD headings.",
    "For Brian meal answers: give totals/notes only; do not repeat back the list of foods he ate.",
    "Never claim durable repo knowledge was updated in this chat turn. A separate scheduled tool-enabled agent ingests knowledge and runs tasks later.",
    "Never say Cursor is running right now or that you dispatched a GitHub workflow.",
    "Classify each message into exactly one route: lightweight_answer, knowledge_update, task, needs_clarification, or ignore.",
    "For knowledge_update or task: acknowledge naturally in one short sentence. The scheduled agent will see the message later — do not over-explain the pipeline.",
    "For lightweight_answer: answer from context when possible.",
    "Keep responses concise and natural for chat.",
    "Return only JSON with keys route, response, async_task_title, async_task_body, confidence.",
  ].join("\n");
  const historyText = history
    .map((turn) => `${turn.role || "unknown"}: ${turn.text || ""}`)
    .join("\n");
  const prompt = [
    "Runtime clock (authoritative):",
    `- Local date: ${clock.localDate}`,
    `- Local time: ${clock.localDisplay}`,
    `- UTC: ${clock.isoUtc}`,
    "",
    "Compact repo context:",
    context,
    "",
    "Recent conversation:",
    historyText || "(none)",
    "",
    `Sender: ${sender.displayName || sender.email || sender.name || "unknown"}`,
    "Incoming message:",
    text,
  ].join("\n");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0.2,
        maxOutputTokens: 700,
        responseMimeType: "application/json",
      },
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(`Gemini API failed: ${response.status} ${JSON.stringify(payload).slice(0, 500)}`);
  }
  const parts = (((payload.candidates || [])[0] || {}).content || {}).parts || [];
  const modelText = parts.map((part) => part.text || "").join("\n").trim();
  return normalizeDecision(parseJsonFromText(modelText), text);
}

function dispatchMetaFromEvent(event) {
  const meta = event && event.agentcore && typeof event.agentcore === "object" ? event.agentcore : {};
  return {
    source_kind: meta.source_kind || "google_chat",
    chat_message_name: meta.message_id || chatMessageName(event),
    chat_space: meta.conversation_id || chatSpaceName(event),
    chat_sender_name: meta.sender_id || senderForEvent(event).name,
    sender_display_name: meta.sender_display_name || senderForEvent(event).displayName,
    telegram_chat_id: meta.telegram_chat_id || "",
    telegram_user_id: meta.telegram_user_id || "",
    telegram_username: meta.telegram_username || "",
    conversation_key: meta.conversation_key || conversationKeyForEvent(event),
  };
}

async function enqueueInboxMessage({ event, text, decision, env = process.env }) {
  const meta = dispatchMetaFromEvent(event);
  if (meta.source_kind !== "telegram") {
    return { status: "not_applicable" };
  }
  return enqueueTelegramMessage(
    {
      message_id: meta.chat_message_name,
      telegram_chat_id: meta.telegram_chat_id,
      telegram_user_id: meta.telegram_user_id,
      telegram_username: meta.telegram_username,
      sender_display_name: meta.sender_display_name,
      conversation_key: meta.conversation_key,
      text,
      route: decision.route,
      confidence: decision.confidence,
      fast_response: decision.response,
      async_task_title: decision.async_task_title || "",
      async_task_body: decision.async_task_body || text,
      received_at: new Date().toISOString(),
    },
    env,
  );
}

async function dispatchAsyncTask({ event, text, decision, env = process.env }) {
  const token = env.GITHUB_DISPATCH_TOKEN || env.GH_DISPATCH_TOKEN || "";
  const repository = env.GITHUB_REPOSITORY || env.AGENTCORE_GITHUB_REPOSITORY || "";
  const eventType = env.AGENTCORE_ROUTER_EVENT_TYPE || "agentcore-router-task";
  if (!token || !repository) {
    return { status: "skipped", reason: "missing_github_dispatch_config" };
  }
  const meta = dispatchMetaFromEvent(event);
  const body = {
    event_type: eventType,
    client_payload: {
      route: decision.route,
      response: decision.response,
      async_task_title:
        decision.async_task_title ||
        (decision.route === "knowledge_update"
          ? meta.source_kind === "telegram"
            ? "Ingest Telegram update"
            : "Ingest Google Chat update"
          : meta.source_kind === "telegram"
            ? "Handle Telegram task"
            : "Handle Telegram task"),
      async_task_body: decision.async_task_body || text,
      source_kind: meta.source_kind,
      chat_message_name: meta.chat_message_name,
      chat_space: meta.chat_space,
      chat_sender_name: meta.chat_sender_name,
      sender_display_name: meta.sender_display_name,
      telegram_chat_id: meta.telegram_chat_id,
      telegram_user_id: meta.telegram_user_id,
      telegram_username: meta.telegram_username,
      conversation_key: meta.conversation_key,
      original_text: text,
      received_at: new Date().toISOString(),
    },
  };
  const response = await fetch(`https://api.github.com/repos/${repository}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "AgentCore-FastRouter",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    return { status: "error", statusCode: response.status, detail: detail.slice(0, 500) };
  }
  return { status: "dispatched", event_type: eventType };
}

async function routeChatEvent(event, options = {}) {
  const env = options.env || process.env;
  const eventType = event && event.type ? event.type : "MESSAGE";
  if (eventType === "ADDED_TO_SPACE") {
    return { text: "AgentCore is here. Send me a message and I’ll either answer quickly or hand it to the deeper repo-backed agent." };
  }
  if (eventType !== "MESSAGE") {
    return { text: "Got it." };
  }

  const text = extractMessageText(event);
  const sender = senderForEvent(event);
  const conversationKey = conversationKeyForEvent(event);
  const context = options.context || buildContext({ rootDir: options.rootDir });
  const history = options.history || (await getHistory(conversationKey, env).catch(() => []));
  let decision;
  const versionAnswer = tryDeterministicVersionAnswer(text, {
    rootDir: options.rootDir,
    env,
    event,
  });
  const deterministic =
    versionAnswer ||
    tryDeterministicFoodAnswer(text, {
      rootDir: options.rootDir,
      env,
      clock: options.clock,
    });
  if (deterministic) {
    decision = normalizeDecision(deterministic, text);
  } else {
    try {
      const modelClient = options.modelClient || callGemini;
      decision = normalizeDecision(await modelClient({ text, context, history, sender, env }), text);
    } catch (error) {
      decision = fallbackDecision(text);
      decision.response = `${decision.response}\n\n(Fast model routing fell back locally.)`;
    }
  }

  let queueStatus = { status: "not_needed" };
  const sourceKind = event && event.agentcore && event.agentcore.source_kind;
  if (sourceKind === "telegram") {
    queueStatus = await enqueueInboxMessage({ event, text, decision, env }).catch(() => ({
      status: "error",
    }));
  }

  const nextHistory = [
    ...history,
    { role: "user", text, at: new Date().toISOString() },
    { role: "assistant", text: decision.response, route: decision.route, at: new Date().toISOString() },
  ];
  await saveHistory(conversationKey, nextHistory, env).catch(() => null);
  const registry = loadVersionRegistry({ rootDir: options.rootDir });
  return {
    text: decision.response,
    _meta: {
      route: decision.route,
      confidence: decision.confidence,
      queue_status: queueStatus.status,
      ...versionMetadata(registry),
    },
    _debug: env.AGENTCORE_ROUTER_DEBUG === "true" ? { decision, queueStatus } : undefined,
  };
}

module.exports = {
  callGemini,
  dispatchAsyncTask,
  enqueueInboxMessage,
  extractMessageText,
  fallbackDecision,
  normalizeDecision,
  routeChatEvent,
  runtimeClock,
};

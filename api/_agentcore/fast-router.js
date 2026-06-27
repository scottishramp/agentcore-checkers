const { buildContext } = require("./context");
const { getHistory, saveHistory } = require("./store");

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
      async_task_title: "Ingest personal update from Google Chat",
      async_task_body: text,
      confidence: 0.5,
    };
  }
  return {
    route: "task",
    response: "Got it. I’ll hand this to the repo-backed Cursor agent for a deeper pass.",
    async_task_title: "Handle Google Chat task",
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
  const system = [
    "You are AgentCore's fast Google Chat router for Brian Herbert and family.",
    "Use the compact repo context to answer only lightweight questions that are immediately answerable.",
    "Do not claim that durable repo knowledge was updated; only the async Cursor agent can write durable updates.",
    "Classify each message into exactly one route: lightweight_answer, knowledge_update, task, needs_clarification, or ignore.",
    "For knowledge_update, acknowledge that the info will be filed later and produce an async task body for Cursor.",
    "For task, acknowledge that the repo-backed Cursor agent will handle it and produce an async task body.",
    "Keep responses concise and natural for Google Chat.",
    "Return only JSON with keys route, response, async_task_title, async_task_body, confidence.",
  ].join("\n");
  const historyText = history
    .map((turn) => `${turn.role || "unknown"}: ${turn.text || ""}`)
    .join("\n");
  const prompt = [
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

async function dispatchAsyncTask({ event, text, decision, env = process.env }) {
  const token = env.GITHUB_DISPATCH_TOKEN || env.GH_DISPATCH_TOKEN || "";
  const repository = env.GITHUB_REPOSITORY || env.AGENTCORE_GITHUB_REPOSITORY || "";
  const eventType = env.AGENTCORE_ROUTER_EVENT_TYPE || "agentcore-router-task";
  if (!token || !repository) {
    return { status: "skipped", reason: "missing_github_dispatch_config" };
  }
  const body = {
    event_type: eventType,
    client_payload: {
      route: decision.route,
      response: decision.response,
      async_task_title: decision.async_task_title || (decision.route === "knowledge_update" ? "Ingest Google Chat update" : "Handle Google Chat task"),
      async_task_body: decision.async_task_body || text,
      source_kind: "google_chat",
      chat_message_name: chatMessageName(event),
      chat_space: chatSpaceName(event),
      chat_sender_name: senderForEvent(event).name,
      sender_display_name: senderForEvent(event).displayName,
      conversation_key: conversationKeyForEvent(event),
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
  try {
    const modelClient = options.modelClient || callGemini;
    decision = normalizeDecision(await modelClient({ text, context, history, sender, env }), text);
  } catch (error) {
    decision = fallbackDecision(text);
    decision.response = `${decision.response}\n\n(Fast model routing fell back locally.)`;
  }

  let dispatch = { status: "not_needed" };
  if (decision.route === "knowledge_update" || decision.route === "task") {
    const dispatcher = options.dispatcher || dispatchAsyncTask;
    dispatch = await dispatcher({ event, text, decision, env });
    if (dispatch.status === "skipped") {
      decision.response = `${decision.response}\n\nAsync handoff is not configured yet, so I may need Brian to run this from Cursor.`;
    } else if (dispatch.status === "error") {
      decision.response = `${decision.response}\n\nI hit a snag handing this to the async runner; I’ll need a Cursor pass to fix the handoff.`;
    }
  }

  const nextHistory = [
    ...history,
    { role: "user", text, at: new Date().toISOString() },
    { role: "assistant", text: decision.response, route: decision.route, at: new Date().toISOString() },
  ];
  await saveHistory(conversationKey, nextHistory, env).catch(() => null);
  return {
    text: decision.response,
    _debug: env.AGENTCORE_ROUTER_DEBUG === "true" ? { decision, dispatch } : undefined,
  };
}

module.exports = {
  callGemini,
  dispatchAsyncTask,
  extractMessageText,
  fallbackDecision,
  normalizeDecision,
  routeChatEvent,
};

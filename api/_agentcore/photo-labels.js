const { runtimeClock } = require("./context");

function compactWhitespace(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function sanitizeUsername(value) {
  return (
    String(value || "user")
      .toLowerCase()
      .replace(/^@/, "")
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "")
      .slice(0, 32) || "user"
  );
}

function localTimestampSeconds(env = process.env) {
  const timezone = env.AGENTCORE_FAST_TIMEZONE || "America/Chicago";
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const pick = (type) => (parts.find((part) => part.type === type) || {}).value || "00";
  return `${pick("year")}${pick("month")}${pick("day")}${pick("hour")}${pick("minute")}${pick("second")}`;
}

function buildPhotoLabel(meta = {}, env = process.env) {
  const username = sanitizeUsername(meta.telegram_username || meta.sender_display_name || meta.telegram_user_id);
  return `${username}_${localTimestampSeconds(env)}`;
}

function geminiApiKey(env = process.env) {
  return env.GOOGLE_AI_STUDIO_API_KEY || env.GEMINI_API_KEY || env.GOOGLE_API_KEY || "";
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

function extractVisibleText(payload) {
  const candidate = (payload && payload.candidates && payload.candidates[0]) || {};
  const parts = (candidate.content && candidate.content.parts) || [];
  return parts
    .filter((part) => !part.thought)
    .map((part) => part.text || "")
    .join("\n")
    .trim();
}

function recoverTruncatedDescription(text) {
  const match = String(text || "").match(/"description"\s*:\s*"([\s\S]*)/);
  if (!match) {
    return "";
  }
  let body = match[1];
  const end = body.search(/"\s*,?\s*}\s*$/);
  if (end >= 0) {
    body = body.slice(0, end);
  }
  return compactWhitespace(body.replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\$/g, ""));
}

function descriptionFromModelText(text) {
  const raw = String(text || "").trim();
  if (!raw) {
    throw new Error("Empty model response.");
  }
  try {
    const parsed = parseJsonFromText(raw);
    if (parsed && typeof parsed.description === "string" && parsed.description.trim()) {
      return compactWhitespace(parsed.description);
    }
  } catch (_error) {
    const recovered = recoverTruncatedDescription(raw);
    if (recovered) {
      return recovered;
    }
  }
  return compactWhitespace(raw);
}

async function describePhotoWithGemini({ inlineMedia, caption, label, env = process.env }) {
  const apiKey = geminiApiKey(env);
  if (!apiKey || !inlineMedia || !inlineMedia.buffer) {
    return {
      description: "Photo received; automatic vision description was unavailable.",
    };
  }
  const model = env.AGENTCORE_FAST_MODEL || "gemini-3.6-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const captionText = caption && caption !== "[photo attached]" ? caption : "(no caption)";
  const system = [
    "You document Telegram photos for AgentCore's multi-agent knowledge system.",
    "Describe only what is visible. Do not invent names, dates, or amounts you cannot read.",
    "Write a thorough description future agents can use without seeing the image: subjects, visible text, document type, setting, people, objects, condition, and actionable details.",
    "Do not acknowledge the user, summarize your task, or add meta-commentary.",
    "Return plain prose only. Do not wrap the answer in JSON or markdown fences.",
  ].join("\n");
  const prompt = [
    `Assigned photo label: ${label}`,
    `User caption: ${captionText}`,
    "Describe this photo in detail for the knowledge base.",
  ].join("\n");
  const timeoutMs = Number(env.AGENTCORE_TELEGRAM_VISION_TIMEOUT_MS || 290000);
  const signal =
    typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 290000)
      : undefined;
  const requestBody = JSON.stringify({
    systemInstruction: { parts: [{ text: system }] },
    contents: [
      {
        role: "user",
        parts: [
          { text: prompt },
          {
            inlineData: {
              mimeType: inlineMedia.mime_type,
              data: inlineMedia.buffer.toString("base64"),
            },
          },
        ],
      },
    ],
    generationConfig: {
      temperature: 0.2,
      maxOutputTokens: 4096,
      thinkingConfig: { thinkingLevel: "minimal" },
    },
  });
  let response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: requestBody,
  });
  let payload = await response.json().catch(() => ({}));
  if ((response.status === 503 || response.status === 429) && !signal?.aborted) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal,
      body: requestBody,
    });
    payload = await response.json().catch(() => ({}));
  }
  if (!response.ok) {
    throw new Error(
      `Gemini photo describe failed: ${response.status} ${JSON.stringify(payload).slice(0, 300)}`,
    );
  }
  const modelText = extractVisibleText(payload);
  if (!modelText) {
    const finish = ((((payload.candidates || [])[0] || {}).finishReason || "") + "") || "unknown";
    throw new Error(`Gemini photo describe returned empty text (finishReason=${finish})`);
  }
  return {
    description: descriptionFromModelText(modelText) || "Photo received; no description returned.",
  };
}

function formatPhotoFastReply({ label, description, caption }) {
  const lines = [`Photo label: ${label}`, "", description || "Photo received."];
  if (caption && caption !== "[photo attached]") {
    lines.push("", `Caption: ${caption}`);
  }
  return lines.join("\n");
}

function buildPhotoTaskBody({ label, description, caption }) {
  const lines = [
    `Photo label: ${label}`,
    "",
    "## Fast-agent description",
    "",
    description || "_No description recorded._",
  ];
  if (caption && caption !== "[photo attached]") {
    lines.push("", "## User caption", "", caption);
  }
  lines.push(
    "",
    "## Cursor instructions",
    "",
    "- This photo was labeled and described by the fast Telegram agent.",
    "- Drive upload and `agentcore/knowledge/communications/telegram-photo-registry.json` should already include the label and Drive URL after materialization.",
    "- File durable knowledge from the description and caption as appropriate.",
    `- End your Telegram reply with exactly these two lines:`,
    `  Photo label: ${label}`,
    "  Drive: <web_view_link from intake notes or registry>",
    `- Update the registry entry for this label with status \"filed\" and any knowledge paths you created.`,
  );
  return lines.join("\n");
}

async function processPhotoMessage({
  event,
  text,
  inlineMedia,
  env = process.env,
  describeClient,
}) {
  const meta = (event && event.agentcore) || {};
  const label = buildPhotoLabel(meta, env);
  const described = await (describeClient || describePhotoWithGemini)({
    inlineMedia,
    caption: text,
    label,
    env,
  }).catch((error) => {
    const message = String(error && error.message ? error.message : error);
    console.log(
      JSON.stringify({
        service: "agentcore-telegram",
        label: "photo_describe_error",
        at: new Date().toISOString(),
        photo_label: label,
        message: message.slice(0, 400),
      }),
    );
    const timedOut = /abort|timeout/i.test(message);
    return {
      description: timedOut
        ? "Photo received; the vision request timed out before Gemini finished."
        : "Photo received; vision description failed.",
    };
  });
  const description = described.description;
  const media = {
    ...(meta.media || {}),
    photo_label: label,
    photo_description: description,
  };
  return {
    label,
    description,
    media,
    decision: {
      route: "knowledge_update",
      response: formatPhotoFastReply({
        label,
        description,
        caption: text,
      }),
      async_task_title: `File photo ${label}`,
      async_task_body: buildPhotoTaskBody({ label, description, caption: text }),
      confidence: 0.88,
    },
  };
}

module.exports = {
  buildPhotoLabel,
  buildPhotoTaskBody,
  describePhotoWithGemini,
  descriptionFromModelText,
  extractVisibleText,
  formatPhotoFastReply,
  localTimestampSeconds,
  processPhotoMessage,
  recoverTruncatedDescription,
  sanitizeUsername,
};

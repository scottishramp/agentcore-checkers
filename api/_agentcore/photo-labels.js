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

async function describePhotoWithGemini({ inlineMedia, caption, label, env = process.env }) {
  const apiKey = geminiApiKey(env);
  if (!apiKey || !inlineMedia || !inlineMedia.buffer) {
    return {
      description: "Photo received; automatic vision description was unavailable.",
    };
  }
  const model = env.AGENTCORE_FAST_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const captionText = caption && caption !== "[photo attached]" ? caption : "(no caption)";
  const system = [
    "You document Telegram photos for AgentCore's multi-agent knowledge system.",
    "Describe only what is visible. Do not invent names, dates, or amounts you cannot read.",
    "Write a thorough description future agents can use without seeing the image: subjects, visible text, document type, setting, people, objects, condition, and actionable details.",
    "Do not acknowledge the user, summarize your task, or add meta-commentary. Return JSON with one key: description.",
  ].join("\n");
  const prompt = [
    `Assigned photo label: ${label}`,
    `User caption: ${captionText}`,
    "Describe this photo in detail for the knowledge base.",
  ].join("\n");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
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
        maxOutputTokens: 900,
        responseMimeType: "application/json",
      },
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(`Gemini photo describe failed: ${response.status}`);
  }
  const parts = (((payload.candidates || [])[0] || {}).content || {}).parts || [];
  const modelText = parts.map((part) => part.text || "").join("\n").trim();
  const parsed = parseJsonFromText(modelText);
  return {
    description: compactWhitespace(parsed.description) || "Photo received; no description returned.",
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
  }).catch(() => ({
    description: "Photo received; vision description failed.",
  }));
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
  formatPhotoFastReply,
  localTimestampSeconds,
  processPhotoMessage,
  sanitizeUsername,
};

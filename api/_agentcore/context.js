const fs = require("fs");
const path = require("path");

const DEFAULT_CONTEXT_FILES = [
  "agentcore/hot-cache.md",
  "agentcore/knowledge/people/brian-herbert.md",
  "agentcore/knowledge/people/herbert-children.md",
  "agentcore/knowledge/documents/life-2026.md",
  "agentcore/knowledge/projects/personal-operating-system.md",
  "agentcore/knowledge/architecture/chatbot-version.json",
  "agentcore/blockers.md",
  "agentcore/index.md",
];

function compactWhitespace(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function readTextIfExists(rootDir, relativePath) {
  const fullPath = path.join(rootDir, relativePath);
  if (!fullPath.startsWith(rootDir)) {
    return "";
  }
  try {
    return fs.readFileSync(fullPath, "utf8");
  } catch (error) {
    if (error && error.code === "ENOENT") {
      return "";
    }
    throw error;
  }
}

function parseFrontmatterValue(content, key) {
  const match = String(content || "").match(new RegExp(`^${key}:\\s*"?([^"\\n]+)"?`, "m"));
  return match ? match[1].trim() : "";
}

function rawChatMessage(content) {
  const marker = "## Raw Chat Message";
  const index = String(content || "").indexOf(marker);
  if (index < 0) {
    return "";
  }
  return compactWhitespace(String(content).slice(index + marker.length));
}

function buildRecentTelegramContext(rootDir, options = {}) {
  const chatDir = path.join(rootDir, "agentcore/inbox/telegram");
  let entries = [];
  try {
    entries = fs
      .readdirSync(chatDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md")
      .map((entry) => {
        const relativePath = path.join("agentcore/inbox/telegram", entry.name);
        const content = readTextIfExists(rootDir, relativePath);
        return {
          receivedAt: parseFrontmatterValue(content, "received_at"),
          sender: parseFrontmatterValue(content, "sender_display_name") || parseFrontmatterValue(content, "telegram_user_id"),
          route: parseFrontmatterValue(content, "route"),
          text: rawChatMessage(content),
        };
      })
      .filter((entry) => entry.receivedAt && entry.text)
      .sort((left, right) => right.receivedAt.localeCompare(left.receivedAt))
      .slice(0, Number(options.limit || 10));
  } catch (error) {
    if (!error || error.code !== "ENOENT") {
      throw error;
    }
  }

  const scheduledState = readTextIfExists(rootDir, "agentcore/knowledge/communications/scheduled-messages-state.json").trim();
  const lines = [];
  if (entries.length) {
    lines.push("Recent Telegram messages tracked for async processing:");
    for (const entry of entries) {
      lines.push(`- ${entry.receivedAt} | ${entry.sender || "unknown"} | ${entry.route || "unknown"}: ${entry.text}`);
    }
  }
  if (scheduledState) {
    lines.push("", "Automation/scheduled message state:", scheduledState);
  }
  return lines.join("\n").trim();
}

function trimMiddle(text, maxChars) {
  if (!maxChars || text.length <= maxChars) {
    return text;
  }
  const keep = Math.max(0, maxChars - 80);
  const head = Math.ceil(keep * 0.65);
  const tail = Math.floor(keep * 0.35);
  return `${text.slice(0, head)}\n\n[...trimmed for fast-router context...]\n\n${text.slice(-tail)}`;
}

function runtimeClock(env = process.env) {
  const timezone = env.AGENTCORE_FAST_TIMEZONE || "America/Chicago";
  const now = new Date();
  const localDate = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
  const localDisplay = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(now);
  return {
    timezone,
    isoUtc: now.toISOString(),
    localDate,
    localDisplay,
  };
}

function addDaysToIsoDate(isoDate, deltaDays) {
  const [year, month, day] = String(isoDate).split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + deltaDays));
  return shifted.toISOString().slice(0, 10);
}

function parseFoodLogByDate(content) {
  const sections = {};
  const lines = String(content || "").split("\n");
  let currentDate = "";
  let buffer = [];
  for (const line of lines) {
    const heading = line.match(/^## (\d{4}-\d{2}-\d{2})\s*$/);
    if (heading) {
      if (currentDate) {
        sections[currentDate] = buffer.join("\n").trim();
      }
      currentDate = heading[1];
      buffer = [];
      continue;
    }
    if (currentDate) {
      buffer.push(line);
    }
  }
  if (currentDate) {
    sections[currentDate] = buffer.join("\n").trim();
  }
  return sections;
}

function extractFoodDaySummary(sectionText) {
  const text = String(sectionText || "");
  const dayTotalMatch = text.match(/\*\*Day total[^*]*\*\*[^\n]*/i);
  if (dayTotalMatch) {
    return compactWhitespace(dayTotalMatch[0].replace(/\*\*/g, ""));
  }
  const runningTotalMatch = text.match(/\*\*Day running total[^*]*\*\*[^\n]*/i);
  if (runningTotalMatch) {
    return compactWhitespace(runningTotalMatch[0].replace(/\*\*/g, ""));
  }
  const mealTotals = [...text.matchAll(/\*\*Meal total:\*\*[^\n]*/g)].map((match) =>
    compactWhitespace(match[0].replace(/\*\*/g, ""))
  );
  if (mealTotals.length) {
    return mealTotals.join("; ");
  }
  return "";
}

function resolveFoodQueryDate(text, clock) {
  const lowered = String(text || "").toLowerCase();
  const explicit = lowered.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
  if (explicit) {
    return explicit[1];
  }
  if (/\byesterday\b/.test(lowered)) {
    return addDaysToIsoDate(clock.localDate, -1);
  }
  if (/\b(today|this morning|tonight|this evening)\b/.test(lowered)) {
    return clock.localDate;
  }
  return "";
}

function tryDeterministicFoodAnswer(text, options = {}) {
  const env = options.env || process.env;
  const rootDir = path.resolve(options.rootDir || process.cwd());
  const lowered = String(text || "").toLowerCase();
  if (!/\b(ate|eat|eating|food|meal|breakfast|lunch|dinner|snack|calories?)\b/.test(lowered)) {
    return null;
  }
  const clock = options.clock || runtimeClock(env);
  const targetDate = resolveFoodQueryDate(text, clock);
  if (!targetDate) {
    return null;
  }

  const foodLog = readTextIfExists(rootDir, "agentcore/knowledge/people/brian-herbert-food-log.md");
  const byDate = parseFoodLogByDate(foodLog);
  const section = byDate[targetDate];
  if (!section) {
    const label = targetDate === clock.localDate ? "today" : targetDate === addDaysToIsoDate(clock.localDate, -1) ? "yesterday" : targetDate;
    return {
      route: "lightweight_answer",
      response: `No food log entries for ${label} (${targetDate}) yet.`,
      confidence: 0.98,
    };
  }

  const summary = extractFoodDaySummary(section);
  const label =
    targetDate === clock.localDate
      ? "Today"
      : targetDate === addDaysToIsoDate(clock.localDate, -1)
        ? "Yesterday"
        : targetDate;
  const response = summary
    ? `${label} (${targetDate}): ${summary.replace(/^Day (?:running )?total(?: \(so far\))?:?\s*/i, "")}`
    : `${label} (${targetDate}): logged, but no totals parsed yet.`;
  return {
    route: "lightweight_answer",
    response,
    confidence: 0.98,
  };
}

function buildContext(options = {}) {
  const rootDir = path.resolve(options.rootDir || process.cwd());
  const files = options.files || DEFAULT_CONTEXT_FILES;
  const maxChars = Number(options.maxChars || process.env.AGENTCORE_FAST_CONTEXT_MAX_CHARS || 24000);

  const sections = [];
  for (const relativePath of files) {
    const content = readTextIfExists(rootDir, relativePath).trim();
    if (!content) {
      continue;
    }
    sections.push(`## ${relativePath}\n\n${content}`);
  }
  const recentTelegramContext = buildRecentTelegramContext(rootDir);
  if (recentTelegramContext) {
    sections.push(`## Recent Telegram Context\n\n${recentTelegramContext}`);
  }

  return trimMiddle(sections.join("\n\n---\n\n"), maxChars);
}

module.exports = {
  DEFAULT_CONTEXT_FILES,
  addDaysToIsoDate,
  buildRecentTelegramContext,
  buildContext,
  extractFoodDaySummary,
  parseFoodLogByDate,
  resolveFoodQueryDate,
  runtimeClock,
  trimMiddle,
  tryDeterministicFoodAnswer,
};

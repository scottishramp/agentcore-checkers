const fs = require("fs");
const path = require("path");

const DEFAULT_CONTEXT_FILES = [
  "agentcore/hot-cache.md",
  "agentcore/blockers.md",
  "agentcore/index.md",
  "agentcore/knowledge/projects/personal-operating-system.md",
  "agentcore/knowledge/people/brian-herbert.md",
  "agentcore/knowledge/people/brian-herbert-food-log.md",
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

function buildRecentChatContext(rootDir, options = {}) {
  const chatDir = path.join(rootDir, "agentcore/inbox/chat");
  let entries = [];
  try {
    entries = fs
      .readdirSync(chatDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".md") && entry.name !== "README.md")
      .map((entry) => {
        const relativePath = path.join("agentcore/inbox/chat", entry.name);
        const content = readTextIfExists(rootDir, relativePath);
        return {
          createdAt: parseFrontmatterValue(content, "created_at"),
          sender: parseFrontmatterValue(content, "sender_display_name") || parseFrontmatterValue(content, "sender_name"),
          text: rawChatMessage(content),
        };
      })
      .filter((entry) => entry.createdAt && entry.text)
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt))
      .slice(0, Number(options.limit || 10));
  } catch (error) {
    if (!error || error.code !== "ENOENT") {
      throw error;
    }
  }

  const scheduledState = readTextIfExists(rootDir, "agentcore/knowledge/communications/scheduled-messages-state.json").trim();
  const lines = [];
  if (entries.length) {
    lines.push("Recent Brian DM messages tracked by the async Chat polling workflow:");
    for (const entry of entries) {
      lines.push(`- ${entry.createdAt} | ${entry.sender || "unknown"}: ${entry.text}`);
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
  const recentChatContext = buildRecentChatContext(rootDir);
  if (recentChatContext) {
    sections.push(`## Recent Google Chat Context\n\n${recentChatContext}`);
  }

  return trimMiddle(sections.join("\n\n---\n\n"), maxChars);
}

module.exports = {
  DEFAULT_CONTEXT_FILES,
  buildRecentChatContext,
  buildContext,
  trimMiddle,
};

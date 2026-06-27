const fs = require("fs");
const path = require("path");

const DEFAULT_CONTEXT_FILES = [
  "agentcore/hot-cache.md",
  "agentcore/blockers.md",
  "agentcore/index.md",
  "agentcore/knowledge/projects/personal-operating-system.md",
  "agentcore/knowledge/people/brian-herbert.md",
];

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

  return trimMiddle(sections.join("\n\n---\n\n"), maxChars);
}

module.exports = {
  DEFAULT_CONTEXT_FILES,
  buildContext,
  trimMiddle,
};

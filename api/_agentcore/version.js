const fs = require("fs");
const path = require("path");

const VERSION_RELATIVE_PATH = "agentcore/knowledge/architecture/chatbot-version.json";

const DEFAULT_REGISTRY = {
  name: "AgentCore Fast Router",
  router_version: "0.0.0",
  context_bundle_version: "0.0.0",
  released_at: "",
  primary_channel: "telegram",
  bot_username: "AgentCoreFam_bot",
  changelog: [],
};

function readJsonIfExists(rootDir, relativePath) {
  const fullPath = path.join(rootDir, relativePath);
  if (!fullPath.startsWith(rootDir)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(fullPath, "utf8"));
  } catch (error) {
    if (error && error.code === "ENOENT") {
      return null;
    }
    throw error;
  }
}

function loadVersionRegistry(options = {}) {
  const rootDir = path.resolve(options.rootDir || process.cwd());
  const registry = readJsonIfExists(rootDir, VERSION_RELATIVE_PATH);
  if (!registry || typeof registry !== "object") {
    return { ...DEFAULT_REGISTRY };
  }
  return {
    ...DEFAULT_REGISTRY,
    ...registry,
    changelog: Array.isArray(registry.changelog) ? registry.changelog : [],
  };
}

function isVersionCommand(text) {
  const normalized = String(text || "").trim().toLowerCase();
  return /^(?:\/)?version[.!?]?$/.test(normalized);
}

function formatVersionResponse(registry, options = {}) {
  const env = options.env || process.env;
  const channel = options.channel || registry.primary_channel || "telegram";
  const model = env.AGENTCORE_FAST_MODEL || "gemini-2.5-flash";
  const lines = [
    `${registry.name} v${registry.router_version}`,
    `Released: ${registry.released_at || "unknown"}`,
    `Context bundle: v${registry.context_bundle_version}`,
    `Channel: ${channel}${registry.bot_username ? ` (@${registry.bot_username})` : ""}`,
    `Model: ${model}`,
  ];
  const latest = registry.changelog[0];
  if (latest && latest.summary) {
    lines.push(`Latest: ${latest.summary}`);
  }
  return lines.join("\n");
}

function versionMetadata(registry) {
  return {
    name: registry.name,
    router_version: registry.router_version,
    context_bundle_version: registry.context_bundle_version,
    released_at: registry.released_at,
  };
}

function tryDeterministicVersionAnswer(text, options = {}) {
  if (!isVersionCommand(text)) {
    return null;
  }
  const registry = loadVersionRegistry(options);
  const channel =
    options.channel ||
    (options.event &&
    options.event.agentcore &&
    options.event.agentcore.source_kind === "telegram"
      ? "telegram"
      : registry.primary_channel);
  return {
    route: "lightweight_answer",
    response: formatVersionResponse(registry, { env: options.env, channel }),
    confidence: 1,
  };
}

module.exports = {
  VERSION_RELATIVE_PATH,
  formatVersionResponse,
  isVersionCommand,
  loadVersionRegistry,
  tryDeterministicVersionAnswer,
  versionMetadata,
};

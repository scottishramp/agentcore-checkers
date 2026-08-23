#!/usr/bin/env node
// Publish the Telegram fast-router knowledge snapshot to Redis.

const fs = require("fs");
const path = require("path");
const { buildContext, contextSnapshot, FAST_CONTEXT_KEY } = require("../../api/_agentcore/context");
const { redisCommand } = require("../../api/_agentcore/store");

function loadDotEnv(filePath) {
  if (!fs.existsSync(filePath)) {
    return;
  }
  for (const line of fs.readFileSync(filePath, "utf8").split("\n")) {
    const match = line.match(/^\s*([A-Z0-9_]+)=(.*)$/);
    if (!match || process.env[match[1]]) {
      continue;
    }
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    process.env[match[1]] = value;
  }
}

async function main() {
  loadDotEnv(path.resolve(".env"));
  const context = buildContext();
  const snap = contextSnapshot({ context });
  const payload = JSON.stringify({
    context,
    context_hash: snap.context_hash,
    context_length: snap.context_length,
    context_files: snap.context_files,
    has_nathan_birthdate: snap.has_nathan_birthdate,
    published_at: new Date().toISOString(),
  });
  const { configured, result } = await redisCommand(["SET", FAST_CONTEXT_KEY, payload]);
  if (!configured) {
    console.error("Redis not configured; skipped fast-context publish.");
    process.exit(1);
  }
  console.log(
    JSON.stringify({
      status: "ok",
      key: FAST_CONTEXT_KEY,
      result,
      context_hash: snap.context_hash,
      context_length: snap.context_length,
      context_files: snap.context_files,
    })
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

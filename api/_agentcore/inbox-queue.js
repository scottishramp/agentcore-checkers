const { redisCommand } = require("./store");

const TELEGRAM_INBOX_KEY = "agentcore:telegram:inbox";

async function enqueueTelegramMessage(record, env = process.env) {
  const payload = JSON.stringify(record);
  const { configured, result } = await redisCommand(["LPUSH", TELEGRAM_INBOX_KEY, payload], env);
  if (!configured) {
    return { status: "skipped", reason: "redis_not_configured" };
  }
  return { status: "queued", inbox_length: result };
}

module.exports = {
  TELEGRAM_INBOX_KEY,
  enqueueTelegramMessage,
};

#!/usr/bin/env node
const { getWebhookInfo, setWebhook } = require("../../api/_agentcore/telegram");

async function main() {
  const webhookUrl =
    process.argv[2] ||
    process.env.AGENTCORE_TELEGRAM_WEBHOOK_URL ||
    "https://agentcore-fast-router.vercel.app/api/agentcore-telegram";
  const result = await setWebhook(webhookUrl);
  const info = await getWebhookInfo();
  console.log(JSON.stringify({ status: "ok", setWebhook: result, webhookInfo: info }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

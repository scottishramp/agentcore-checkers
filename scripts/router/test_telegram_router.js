#!/usr/bin/env node
const assert = require("assert");
const { routeChatEvent } = require("../../api/_agentcore/fast-router");
const { updateToEvent } = require("../../api/_agentcore/telegram");

async function run() {
  const update = {
    update_id: 123,
    message: {
      message_id: 456,
      text: "What did I eat yesterday?",
      chat: { id: 999001, type: "private" },
      from: { id: 111, first_name: "Brian", username: "brianh" },
    },
  };
  const event = updateToEvent(update);
  assert(event, "telegram update should map to router event");
  assert.equal(event.agentcore.source_kind, "telegram");
  assert.equal(event.agentcore.telegram_chat_id, "999001");

  const routed = await routeChatEvent(event, {
    history: [],
    env: {},
    modelClient: async () => ({
      route: "lightweight_answer",
      response: "Checking the food log now.",
      confidence: 0.9,
    }),
  });
  assert.match(routed.text, /Checking the food log/);

  let payload = null;
  await routeChatEvent(event, {
    history: [],
    env: {},
    modelClient: async () => ({
      route: "task",
      response: "On it.",
      async_task_title: "Research flights",
      async_task_body: "Find flights OKC to PHL",
      confidence: 0.8,
    }),
    dispatcher: async ({ event: routedEvent, decision }) => {
      payload = { source_kind: routedEvent.agentcore.source_kind, route: decision.route };
      return { status: "dispatched" };
    },
  });
  assert(payload);
  assert.equal(payload.source_kind, "telegram");

  console.log("telegram router tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

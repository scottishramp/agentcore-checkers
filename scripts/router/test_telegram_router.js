#!/usr/bin/env node
const assert = require("assert");
const { routeChatEvent } = require("../../api/_agentcore/fast-router");
const { isUserAllowed, updateToEvent } = require("../../api/_agentcore/telegram");

async function run() {
  assert.equal(isUserAllowed("8983527816", { AGENTCORE_TELEGRAM_ALLOWED_USER_IDS: "" }), false);
  assert.equal(isUserAllowed("8983527816", { AGENTCORE_TELEGRAM_ALLOWED_USER_IDS: "8983527816" }), true);
  assert.equal(isUserAllowed("999", { AGENTCORE_TELEGRAM_ALLOWED_USER_IDS: "8983527816" }), false);
  assert.equal(
    isUserAllowed("222", { AGENTCORE_TELEGRAM_ALLOWED_USER_IDS: "8983527816, 222" }),
    true,
  );
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

  const routed = await routeChatEvent(
    {
      ...updateToEvent({
        update_id: 124,
        message: {
          message_id: 457,
          text: "hello",
          chat: { id: 999001, type: "private" },
          from: { id: 111, first_name: "Brian", username: "brianh" },
        },
      }),
    },
    {
      history: [],
      env: {},
      modelClient: async () => ({
        route: "lightweight_answer",
        response: "Hi Brian — I'm here.",
        confidence: 0.9,
      }),
    },
  );
  assert.match(routed.text, /I'm here/);

  const food = await routeChatEvent(event, {
    history: [],
    env: {},
    clock: { localDate: "2026-06-27", timezone: "America/Chicago", localDisplay: "Saturday, June 27, 2026", isoUtc: "2026-06-27T00:00:00.000Z" },
    modelClient: async () => {
      throw new Error("Gemini should not run for deterministic food lookup");
    },
  });
  assert.match(food.text, /2026-06-26/);

  const taskEvent = updateToEvent({
    update_id: 125,
    message: {
      message_id: 458,
      text: "Find flights OKC to PHL",
      chat: { id: 999001, type: "private" },
      from: { id: 111, first_name: "Brian", username: "brianh" },
    },
  });
  const taskRouted = await routeChatEvent(taskEvent, {
    history: [],
    env: {},
    modelClient: async () => ({
      route: "task",
      response: "On it.",
      async_task_title: "Research flights",
      async_task_body: "Find flights OKC to PHL",
      confidence: 0.8,
    }),
  });
  assert.equal(taskRouted._meta.route, "task");
  assert.equal(taskRouted._meta.queue_status, "skipped");

  console.log("telegram router tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

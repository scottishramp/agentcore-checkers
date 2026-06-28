#!/usr/bin/env node
const assert = require("assert");
const { routeChatEvent } = require("../../api/_agentcore/fast-router");
const { buildContext } = require("../../api/_agentcore/context");

function eventWithText(text) {
  return {
    type: "MESSAGE",
    user: {
      name: "users/111231822876595172958",
      displayName: "Brian Herbert",
      email: "briandherbert@gmail.com",
    },
    space: { name: "spaces/test-space" },
    message: {
      name: "spaces/test-space/messages/test-message",
      text,
      thread: { name: "spaces/test-space/threads/test-thread" },
    },
  };
}

async function run() {
  const context = buildContext({ rootDir: process.cwd() });
  assert(context.includes("AgentCore"), "context should include AgentCore knowledge");
  assert(context.includes("herbert-children"), "context should include family knowledge pages");

  const food = await routeChatEvent(eventWithText("what did I eat yesterday?"), {
    context,
    history: [],
    env: { AGENTCORE_ROUTER_DEBUG: "true" },
    clock: { localDate: "2026-06-27", timezone: "America/Chicago", localDisplay: "Saturday, June 27, 2026", isoUtc: "2026-06-27T00:00:00.000Z" },
    modelClient: async () => {
      throw new Error("Gemini should not be called for deterministic food lookup");
    },
  });
  assert.match(food.text, /2026-06-26/);
  assert.match(food.text, /2,030|2030/);

  const version = await routeChatEvent(eventWithText("version"), {
    context,
    history: [],
    env: {},
    modelClient: async () => {
      throw new Error("Gemini should not run for version command");
    },
  });
  assert.match(version.text, /AgentCore Fast Router v2\.3\.0/);
  assert.match(version.text, /Context bundle: v2\.2\.1/);

  const lightweight = await routeChatEvent(eventWithText("What is my food check-in prompt?"), {
    context,
    history: [],
    env: { AGENTCORE_ROUTER_DEBUG: "true" },
    modelClient: async () => ({
      route: "lightweight_answer",
      response: "Your food check-in prompt is: What'd you eat since last time?",
      confidence: 0.95,
    }),
  });
  assert.match(lightweight.text, /What'd you eat since last time/);

  const knowledgeEvent = {
    ...eventWithText("I had eggs and sourdough for breakfast"),
    agentcore: {
      source_kind: "telegram",
      message_id: "telegram:test-knowledge",
      telegram_chat_id: "999001",
      telegram_user_id: "111",
      conversation_key: "telegram:dm:999001",
    },
    space: { name: "telegram:dm:999001" },
  };
  const update = await routeChatEvent(knowledgeEvent, {
    context,
    history: [],
    env: { AGENTCORE_ROUTER_DEBUG: "true" },
    modelClient: async () => ({
      route: "knowledge_update",
      response: "Got it — I'll note that for the scheduled agent.",
      async_task_title: "Log Brian breakfast",
      async_task_body: "Brian had eggs and sourdough for breakfast.",
      confidence: 0.9,
    }),
  });
  assert.match(update.text, /scheduled agent/i);
  assert.equal(update._meta.queue_status, "skipped");

  const taskEvent = {
    ...eventWithText("Build me a little scheduling app"),
    agentcore: {
      source_kind: "telegram",
      message_id: "telegram:test-task",
      telegram_chat_id: "999001",
      telegram_user_id: "111",
      conversation_key: "telegram:dm:999001",
    },
    space: { name: "telegram:dm:999001" },
  };
  const task = await routeChatEvent(taskEvent, {
    context,
    history: [],
    env: {},
    modelClient: async () => ({
      route: "task",
      response: "Got it — the scheduled repo agent will pick this up.",
      async_task_title: "Build scheduling app",
      async_task_body: "Build a small scheduling app prototype.",
      confidence: 0.88,
    }),
  });
  assert.match(task.text, /scheduled repo agent/i);
  assert.equal(task._meta.queue_status, "skipped");

  console.log("fast router tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

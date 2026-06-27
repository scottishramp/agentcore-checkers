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
  const context = buildContext({ rootDir: process.cwd(), maxChars: 12000 });
  assert(context.includes("AgentCore"), "context should include AgentCore knowledge");

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

  let dispatchedPayload = null;
  const update = await routeChatEvent(eventWithText("I had eggs and sourdough for breakfast"), {
    context,
    history: [],
    env: { AGENTCORE_ROUTER_DEBUG: "true" },
    modelClient: async () => ({
      route: "knowledge_update",
      response: "Got it. I’ll queue that for the food log.",
      async_task_title: "Log Brian breakfast",
      async_task_body: "Brian had eggs and sourdough for breakfast.",
      confidence: 0.9,
    }),
    dispatcher: async (payload) => {
      dispatchedPayload = payload;
      return { status: "dispatched" };
    },
  });
  assert.match(update.text, /queue that/);
  assert(dispatchedPayload, "knowledge update should dispatch async task");
  assert.equal(dispatchedPayload.decision.route, "knowledge_update");

  let taskDispatched = false;
  const task = await routeChatEvent(eventWithText("Build me a little scheduling app"), {
    context,
    history: [],
    env: {},
    modelClient: async () => ({
      route: "task",
      response: "Got it. I’ll hand that to the repo-backed agent.",
      async_task_title: "Build scheduling app",
      async_task_body: "Build a small scheduling app prototype.",
      confidence: 0.88,
    }),
    dispatcher: async () => {
      taskDispatched = true;
      return { status: "dispatched" };
    },
  });
  assert.match(task.text, /repo-backed agent/);
  assert.equal(taskDispatched, true);

  console.log("fast router tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

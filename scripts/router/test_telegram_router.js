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

  const photoUpdate = {
    update_id: 126,
    message: {
      message_id: 459,
      caption: "Receipt from lunch",
      photo: [
        { file_id: "small", width: 90, height: 90, file_size: 1000 },
        { file_id: "large-photo-id", width: 1280, height: 960, file_size: 50000 },
      ],
      chat: { id: 999001, type: "private" },
      from: { id: 111, first_name: "Brian", username: "brianh" },
    },
  };
  const photoEvent = updateToEvent(photoUpdate);
  assert(photoEvent, "photo update should map to router event");
  assert.equal(photoEvent.message.text, "Receipt from lunch");
  assert.equal(photoEvent.agentcore.media.telegram_file_id, "large-photo-id");
  assert.equal(photoEvent.agentcore.media.type, "photo");

  const captionlessPhoto = updateToEvent({
    update_id: 127,
    message: {
      message_id: 460,
      photo: [{ file_id: "solo-photo", width: 800, height: 600 }],
      chat: { id: 999001, type: "private" },
      from: { id: 111, first_name: "Brian" },
    },
  });
  assert.equal(captionlessPhoto.message.text, "[photo attached]");
  assert.equal(captionlessPhoto.agentcore.media.telegram_file_id, "solo-photo");

  const photoRouted = await routeChatEvent(photoEvent, {
    history: [],
    env: { AGENTCORE_FAST_VISION: "false" },
    describePhotoClient: async () => ({
      description: "A crumpled paper receipt with itemized lunch charges.",
    }),
  });
  assert.equal(photoRouted._meta.route, "knowledge_update");
  assert.equal(photoRouted._meta.has_media, true);
  assert.match(photoRouted._meta.photo_label, /^brianh_/);
  assert.match(photoRouted.text, /Photo label:/);
  assert.match(photoRouted.text, /receipt/i);
  assert.ok(photoRouted.text.includes("\n\n"), "photo reply should keep paragraph breaks");
  assert.doesNotMatch(photoRouted.text, /Caption:.*Got the receipt/);

  console.log("telegram router tests passed");
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});

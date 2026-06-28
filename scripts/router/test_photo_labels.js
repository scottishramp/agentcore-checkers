#!/usr/bin/env node
const assert = require("assert");
const { buildPhotoLabel, formatPhotoFastReply, processPhotoMessage } = require("../../api/_agentcore/photo-labels");

assert.match(buildPhotoLabel({ telegram_username: "brianh" }, { AGENTCORE_FAST_TIMEZONE: "America/Chicago" }), /^brianh_\d{14}$/);

const reply = formatPhotoFastReply({
  label: "brianh_20260627143045",
  description: "A paper receipt on a wooden table showing a lunch total.",
  caption: "Receipt from lunch",
});
assert.match(reply, /Photo label: brianh_20260627143045/);
assert.match(reply, /receipt on a wooden table/i);
assert.match(reply, /Caption: Receipt from lunch/);
assert.doesNotMatch(reply, /I'll file/);
assert.ok(reply.includes("\n\n"), "photo reply should preserve paragraph breaks");

(async () => {
  const photoResult = await processPhotoMessage({
    event: {
      agentcore: {
        telegram_username: "brianh",
        media: { telegram_file_id: "abc", type: "photo" },
      },
    },
    text: "Insurance card",
    inlineMedia: null,
    env: {},
    describeClient: async () => ({
      description: "Photo of a health insurance member ID card with visible policy number area.",
    }),
  });
  assert.match(photoResult.label, /^brianh_/);
  assert.match(photoResult.decision.response, /Photo label:/);
  assert.match(photoResult.decision.response, /health insurance/i);
  assert.match(photoResult.decision.async_task_body, /Photo label:/);
  console.log("photo label tests passed");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

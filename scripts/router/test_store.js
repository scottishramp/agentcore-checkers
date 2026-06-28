#!/usr/bin/env node
const assert = require("assert");
const {
  historyMessageLimit,
  historyTtlSeconds,
} = require("../../api/_agentcore/store");

assert.equal(historyMessageLimit({}), 20);
assert.equal(historyMessageLimit({ AGENTCORE_FAST_HISTORY_MESSAGES: "25" }), 25);
assert.equal(historyMessageLimit({ AGENTCORE_FAST_HISTORY_TURNS: "8" }), 16);
assert.equal(historyTtlSeconds({}), 0);
assert.equal(historyTtlSeconds({ AGENTCORE_FAST_HISTORY_TTL_SECONDS: "3600" }), 3600);
assert.equal(historyTtlSeconds({ AGENTCORE_FAST_HISTORY_TTL_SECONDS: "0" }), 0);
assert.equal(historyTtlSeconds({ AGENTCORE_FAST_HISTORY_TTL_SECONDS: "none" }), 0);

console.log("store tests passed");

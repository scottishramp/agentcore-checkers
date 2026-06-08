# Google Chat Inbox Records

Normalized Google Chat messages that should be processed by AgentCore jobs.

- Source channel: Brian's direct message space with AgentCore in Google Chat.
- Current DM space: `spaces/6RZ69yAAAAE`.
- Direct Chat messages from Brian are instructions by default and should be queued for the async runner.
- AgentCore replies should be sent back to the same Chat space, with task IDs and runner metadata omitted unless Brian asks for diagnostics.
- Idempotency is tracked in `agentcore/knowledge/communications/chat-thread-ledger.json`; raw sensitive content should stay minimal.

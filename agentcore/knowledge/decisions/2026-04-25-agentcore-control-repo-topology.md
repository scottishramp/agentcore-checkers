---
title: AgentCore control repo with separate delivery repos
type: decision
status: accepted
created: 2026-04-25
updated: 2026-04-25
deciders:
  - AgentCore
  - Brian Herbert
confidence: high
related:
  - ../playbooks/email-ops.md
  - ../projects/checkers-web-game.md
---

# Decision: AgentCore control repo with separate delivery repos

## Status

Accepted

## Context

AgentCore needs a durable home for operating instructions, knowledge memory, asynchronous communication tooling, and automation workflows. At the same time, client jobs should remain easy to review, ship, and archive without coupling every project to the operating repository history.

## Decision

Use this repository as the AgentCore control repo (memory + procedures + communication automation), and create separate repositories for individual client job deliverables by default.

## Rationale

- The control system evolves continuously and should not be reset per project.
- Project repos stay focused, smaller, and easier to hand off.
- CI and release settings can vary per client job without destabilizing AgentCore operations.
- Cross-project knowledge still compounds through `agentcore/knowledge/`.

## Consequences

- AgentCore must maintain links between project repos and local knowledge pages.
- Some workflows require context switching across repositories.
- Shared tooling should be versioned in the control repo and reused intentionally.

## Alternatives Considered

- Single monorepo for all client jobs: simpler centralization, but noisy history and weaker project isolation.
- Fully separate repos with no control repo: stronger isolation, but loses durable operating memory.

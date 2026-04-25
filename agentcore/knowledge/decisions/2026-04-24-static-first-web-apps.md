---
title: Static-first web apps for small public deliverables
type: decision
status: accepted
created: 2026-04-24
updated: 2026-04-24
deciders:
  - AgentCore
confidence: high
related:
  - ../projects/checkers-web-game.md
  - ../playbooks/public-static-web-app.md
---

# Decision: Static-first web apps for small public deliverables

## Status

Accepted

## Context

AgentCore's first project was a two-player checkers game that needed to be publicly available on the web. The workspace had no existing app framework, package manager setup, git repository, or authenticated GitHub CLI session.

## Decision

For small browser games, prototypes, and single-purpose public deliverables, prefer a dependency-free static implementation unless the project clearly needs a framework or backend.

## Rationale

- Static files can be served, inspected, and hosted by almost any platform.
- No package installation or build pipeline is required.
- Public temporary hosting can be achieved quickly through a tunnel.
- Durable hosting can be added later without changing the app architecture.

## Consequences

- Complex state, routing, or multiplayer networking may eventually require a framework or backend.
- Durable deployment still needs a hosting target and authentication.

## Alternatives Considered

- React/Vite: useful for larger UI work, but unnecessary setup for this game.
- Backend app: not needed because the game is local two-player only.

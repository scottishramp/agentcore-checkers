---
title: UX message design
type: concept
status: active
created: 2026-04-24
updated: 2026-04-24
confidence: high
related:
  - ../projects/checkers-web-game.md
  - ../playbooks/public-static-web-app.md
---

# Concept: UX Message Design

## Core Principle

Every user-visible status or error message must classify the exact failure reason. A catch-all message is usually wrong for at least one valid state.

## The Classification Pattern

Before writing a message, enumerate every state the user can arrive at. For each distinct state, write a distinct message:

| State | Bad message | Good message |
|---|---|---|
| Piece has no moves (surrounded) | "That piece has no legal moves." | "That piece is blocked. Select a highlighted piece." |
| Another piece must capture first | "That piece has no legal moves." | "A capture is required. Select a highlighted capturing piece." |
| Player has no moves at all | "That piece has no legal moves." | "No valid moves remain for Red." |
| Game is over | *(silent)* | "Black wins. Red has no valid moves remaining." |

The bad message was literally used in the checkers game and confused users for every case except the one it was originally written for.

## Messages Are Testable Behavior

Status messages are not cosmetic. They communicate game state. Write automated assertions for them:

```javascript
await expect(page.locator("#statusText")).toContainText(
  "A capture is required. Select a highlighted capturing piece."
);
```

When message logic changes, update the assertions immediately. If you change the message, the test should break until it is also updated.

## Do Not Blame the Rules on the Piece

Saying "that piece has no legal moves" when the real reason is a mandatory-capture rule elsewhere blames the selected piece for a constraint it did not create. This frustrates users.

Correct framing:
- The piece is the subject only when the piece itself is the reason.
- If a game rule prevents selection, cite the rule.

## Hierarchy of Messages

In games and interactive tools, render messages in this priority order so lower-priority messages do not mask higher-priority ones:

1. Game over.
2. Forced continuation (must keep jumping with same piece).
3. Rule constraint (capture required).
4. Selection guidance (select a highlighted piece).
5. Idle state (X to move).

## Practical Checklist

Before shipping any user-visible message:

- [ ] Does this message cover only the state it describes?
- [ ] Is there any other state that could produce this message incorrectly?
- [ ] Is there an automated assertion for this message?
- [ ] Does the message tell the user what to do next, not just what went wrong?

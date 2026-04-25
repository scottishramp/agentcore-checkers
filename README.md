# AgentCore Checkers

A dependency-free, browser-based checkers game for two local players.

## Play Locally

Open `index.html` in a browser, or serve the folder with any static file server.

```sh
python3 -m http.server 4173
```

Then visit `http://localhost:4173`.

## Features

- Two-player local play.
- Mandatory captures.
- Multi-jump continuation.
- King pieces.
- Undo and restart controls.
- Responsive layout for desktop and mobile.

## Prototype Test Scenarios

Use this checklist before sharing updates:

1. **Initial state**: red turn, 12 red pieces, 12 black pieces, zero captures.
2. **Simple legal move**: select a movable red piece, see legal destination marker, complete move, turn flips to black.
3. **Blocked piece behavior**: selecting a blocked piece shows guidance to choose a highlighted movable piece.
4. **Mandatory capture**: set up and validate that only capture moves are allowed when a capture exists.
5. **Multi-jump**: after a capture that enables another capture, same piece is forced to continue.
6. **Kinging**: move a piece to back rank and confirm king marker and reverse-direction movement.
7. **Undo**: make a move, undo it, and confirm board/turn restoration.
8. **Restart**: restart resets board, captures, turn, and game state.
9. **Responsive layout**: verify board proportions and control readability on desktop and mobile widths.

See `tests/user-test-suite.md` for the full manual suite and `tests/checkers.user.spec.js` for automated scenarios.

## Run Automated User Tests

```sh
npm test
```

## Deployment

The app is static and can be published by any static host, including GitHub Pages, Netlify, Vercel, Cloudflare Pages, or an object-storage bucket with website hosting.

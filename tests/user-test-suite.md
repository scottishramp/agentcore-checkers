# Checkers User Test Suite

Use this suite before sharing prototype updates.

## Functional Tests

1. **Initial state**
   - Open app.
   - Expect: 12 red pieces, 12 black pieces, red turn, captured counts at 0.
2. **Movable piece discoverability**
   - Expect only currently movable piece origins to be visually highlighted.
3. **Blocked piece guidance**
   - Click a blocked piece.
   - Expect guidance text to explain it's blocked and to choose a highlighted piece.
4. **Legal move flow**
   - Select a movable piece and move it.
   - Expect turn changes and status updates.
5. **Mandatory capture**
   - In a capture-available scenario, try a non-capturing piece.
   - Expect non-capturing piece rejected and capture piece highlighted.
6. **Multi-jump**
   - Perform a capture that enables a second capture.
   - Expect forced continuation with same piece until chain ends.
7. **Kinging**
   - Reach back rank with non-king piece.
   - Expect king marker and reverse movement capability.
8. **Undo**
   - Make move, undo.
   - Expect board and turn rollback.
9. **Restart**
   - Restart after several moves.
   - Expect clean initial board state.
10. **Win condition**
   - Reach state where player has no valid moves.
   - Expect game-over status and no further play.

## UX And Visual Tests

1. **Board geometry**
   - Verify all 8 rows and 8 columns are uniform with no squished center rows.
2. **Status clarity**
   - Verify status text reflects current interaction and does not show misleading errors.
3. **Control usability**
   - Verify Undo/Restart are reachable and obvious on desktop and mobile.
4. **Mobile responsiveness**
   - Verify board stays square and readable around 390x844 viewport.
5. **Color/contrast sanity**
   - Verify pieces, legal markers, and status text are legible against background.

## Automated Run

- `npm test` executes automated user-scenario tests in `tests/checkers.user.spec.js`.

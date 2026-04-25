const RED = "red";
const BLACK = "black";
const BOARD_SIZE = 8;

const boardEl = document.querySelector("#board");
const turnTextEl = document.querySelector("#turnText");
const statusTextEl = document.querySelector("#statusText");
const redCapturedEl = document.querySelector("#redCaptured");
const blackCapturedEl = document.querySelector("#blackCaptured");
const undoButton = document.querySelector("#undoButton");
const restartButton = document.querySelector("#restartButton");

let board = createInitialBoard();
let currentPlayer = RED;
let selected = null;
let legalMoves = [];
let mustContinueFrom = null;
let history = [];
let gameOver = false;

render();

restartButton.addEventListener("click", restartGame);
undoButton.addEventListener("click", undoMove);
attachTestApi();

function createInitialBoard() {
  return Array.from({ length: BOARD_SIZE }, (_, row) =>
    Array.from({ length: BOARD_SIZE }, (_, col) => {
      if (!isDarkSquare(row, col)) return null;
      if (row < 3) return { color: BLACK, king: false };
      if (row > 4) return { color: RED, king: false };
      return null;
    }),
  );
}

function createEmptyBoard() {
  return Array.from({ length: BOARD_SIZE }, () =>
    Array.from({ length: BOARD_SIZE }, () => null),
  );
}

function render(message) {
  boardEl.innerHTML = "";
  const allMoves = getLegalMovesForPlayer(board, currentPlayer, mustContinueFrom);
  const selectedKey = selected ? toKey(selected) : null;
  const legalByDestination = new Map(legalMoves.map((move) => [toKey(move.to), move]));
  const movableOrigins = new Set(allMoves.map((move) => toKey(move.from)));

  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const square = document.createElement("button");
      const piece = board[row][col];
      const key = toKey({ row, col });
      const legalMove = legalByDestination.get(key);

      square.type = "button";
      square.className = `square ${isDarkSquare(row, col) ? "dark" : "light"}`;
      square.dataset.row = row;
      square.dataset.col = col;
      square.setAttribute("role", "gridcell");
      square.setAttribute("aria-label", describeSquare(row, col, piece, legalMove));

      if (key === selectedKey) square.classList.add("selected");
      if (!selected && !mustContinueFrom && movableOrigins.has(key)) {
        square.classList.add("movable");
      }
      if (legalMove) {
        square.classList.add("legal");
        if (legalMove.capture) square.classList.add("capture");
      }

      if (piece) {
        const pieceEl = document.createElement("span");
        pieceEl.className = `piece ${piece.color} ${piece.king ? "king" : ""}`;
        square.append(pieceEl);
      }

      square.addEventListener("click", () => handleSquareClick(row, col));
      boardEl.append(square);
    }
  }

  const redCaptured = 12 - countPieces(board, RED);
  const blackCaptured = 12 - countPieces(board, BLACK);
  redCapturedEl.textContent = String(redCaptured);
  blackCapturedEl.textContent = String(blackCaptured);
  turnTextEl.textContent = gameOver ? "Game Over" : capitalize(currentPlayer);
  undoButton.disabled = history.length === 0;

  if (message) {
    statusTextEl.textContent = message;
  } else if (gameOver) {
    statusTextEl.textContent = `${capitalize(opponent(currentPlayer))} wins.`;
  } else if (mustContinueFrom) {
    statusTextEl.textContent = `${capitalize(currentPlayer)} must continue the jump.`;
  } else if (allMoves.some((move) => move.capture)) {
    statusTextEl.textContent = `${capitalize(currentPlayer)} must capture.`;
  } else {
    statusTextEl.textContent = `${capitalize(currentPlayer)} to move. Select a highlighted piece.`;
  }
}

function handleSquareClick(row, col) {
  if (gameOver) return;

  const allMoves = getLegalMovesForPlayer(board, currentPlayer, mustContinueFrom);
  const clicked = { row, col };
  const piece = board[row][col];
  const destinationMove = legalMoves.find((move) => samePosition(move.to, clicked));

  if (destinationMove) {
    makeMove(destinationMove);
    return;
  }

  if (!piece || piece.color !== currentPlayer) {
    clearSelection("Select one of your pieces.");
    return;
  }

  if (mustContinueFrom && !samePosition(mustContinueFrom, clicked)) {
    clearSelection("You must continue jumping with the same piece.");
    return;
  }

  const playerMoves = getLegalMovesForPlayer(board, currentPlayer, mustContinueFrom);
  const movesForPiece = playerMoves.filter((move) => samePosition(move.from, clicked));

  if (movesForPiece.length === 0) {
    if (allMoves.length === 0) {
      clearSelection(`No valid moves remain for ${capitalize(currentPlayer)}.`);
      return;
    }
    if (allMoves.some((move) => move.capture)) {
      clearSelection("A capture is required. Select a highlighted capturing piece.");
      return;
    }
    clearSelection("That piece is blocked. Select a highlighted piece.");
    return;
  }

  selected = clicked;
  legalMoves = movesForPiece;
  render(`${capitalize(currentPlayer)} selected ${positionName(clicked)}.`);
}

function makeMove(move) {
  history.push({
    board: cloneBoard(board),
    currentPlayer,
    selected,
    legalMoves,
    mustContinueFrom,
    gameOver,
  });

  const movingPiece = board[move.from.row][move.from.col];
  board[move.to.row][move.to.col] = movingPiece;
  board[move.from.row][move.from.col] = null;

  if (move.capture) {
    board[move.capture.row][move.capture.col] = null;
  }

  const crowned = maybeCrown(movingPiece, move.to.row);
  const followUpCaptures = move.capture && !crowned
    ? getMovesForPiece(board, move.to, true)
    : [];

  if (followUpCaptures.length > 0) {
    selected = move.to;
    legalMoves = followUpCaptures;
    mustContinueFrom = move.to;
    render(`${capitalize(currentPlayer)} captured and must continue jumping.`);
    return;
  }

  currentPlayer = opponent(currentPlayer);
  selected = null;
  legalMoves = [];
  mustContinueFrom = null;

  if (isGameOver()) {
    gameOver = true;
    render(`${capitalize(opponent(currentPlayer))} wins. ${capitalize(currentPlayer)} has no valid moves remaining.`);
    return;
  }

  const message = move.capture
    ? `${capitalize(opponent(currentPlayer))} captured. ${capitalize(currentPlayer)} to move.`
    : `${capitalize(currentPlayer)} to move.`;
  render(message);
}

function maybeCrown(piece, row) {
  if (piece.king) return false;
  if ((piece.color === RED && row === 0) || (piece.color === BLACK && row === BOARD_SIZE - 1)) {
    piece.king = true;
    return true;
  }
  return false;
}

function getLegalMovesForPlayer(currentBoard, player, requiredFrom = null) {
  const moves = [];

  for (let row = 0; row < BOARD_SIZE; row += 1) {
    for (let col = 0; col < BOARD_SIZE; col += 1) {
      const from = { row, col };
      const piece = currentBoard[row][col];
      if (!piece || piece.color !== player) continue;
      if (requiredFrom && !samePosition(requiredFrom, from)) continue;
      moves.push(...getMovesForPiece(currentBoard, from, false));
    }
  }

  const captures = moves.filter((move) => move.capture);
  return captures.length > 0 ? captures : moves;
}

function getMovesForPiece(currentBoard, from, capturesOnly) {
  const piece = currentBoard[from.row][from.col];
  if (!piece) return [];

  const moves = [];
  for (const direction of directionsFor(piece)) {
    const adjacent = {
      row: from.row + direction.row,
      col: from.col + direction.col,
    };
    const landing = {
      row: from.row + direction.row * 2,
      col: from.col + direction.col * 2,
    };

    if (!isOnBoard(adjacent)) continue;

    const adjacentPiece = currentBoard[adjacent.row][adjacent.col];
    if (
      adjacentPiece &&
      adjacentPiece.color !== piece.color &&
      isOnBoard(landing) &&
      currentBoard[landing.row][landing.col] === null
    ) {
      moves.push({ from, to: landing, capture: adjacent });
      continue;
    }

    if (!capturesOnly && !adjacentPiece) {
      moves.push({ from, to: adjacent, capture: null });
    }
  }

  return moves;
}

function directionsFor(piece) {
  if (piece.king) {
    return [
      { row: -1, col: -1 },
      { row: -1, col: 1 },
      { row: 1, col: -1 },
      { row: 1, col: 1 },
    ];
  }

  const rowDirection = piece.color === RED ? -1 : 1;
  return [
    { row: rowDirection, col: -1 },
    { row: rowDirection, col: 1 },
  ];
}

function isGameOver() {
  return countPieces(board, currentPlayer) === 0 ||
    getLegalMovesForPlayer(board, currentPlayer).length === 0;
}

function setStateForTesting(nextState) {
  board = cloneBoard(nextState.board);
  currentPlayer = nextState.currentPlayer ?? RED;
  selected = nextState.selected ?? null;
  legalMoves = [];
  mustContinueFrom = nextState.mustContinueFrom ?? null;
  history = [];
  gameOver = nextState.gameOver ?? false;
  render(nextState.message);
}

function getStateSnapshot() {
  return {
    board: cloneBoard(board),
    currentPlayer,
    selected: selected ? { ...selected } : null,
    mustContinueFrom: mustContinueFrom ? { ...mustContinueFrom } : null,
    gameOver,
  };
}

function attachTestApi() {
  window.__checkersTest = {
    createEmptyBoard,
    setState: setStateForTesting,
    getState: getStateSnapshot,
    restart: restartGame,
  };
}

function restartGame() {
  board = createInitialBoard();
  currentPlayer = RED;
  selected = null;
  legalMoves = [];
  mustContinueFrom = null;
  history = [];
  gameOver = false;
  render("New game started. Red moves first.");
}

function undoMove() {
  const previous = history.pop();
  if (!previous) return;

  board = previous.board;
  currentPlayer = previous.currentPlayer;
  selected = previous.selected;
  legalMoves = previous.legalMoves;
  mustContinueFrom = previous.mustContinueFrom;
  gameOver = previous.gameOver;
  render("Move undone.");
}

function clearSelection(message) {
  selected = null;
  legalMoves = [];
  render(message);
}

function countPieces(currentBoard, color) {
  return currentBoard.flat().filter((piece) => piece?.color === color).length;
}

function cloneBoard(currentBoard) {
  return currentBoard.map((row) => row.map((piece) => piece ? { ...piece } : null));
}

function isDarkSquare(row, col) {
  return (row + col) % 2 === 1;
}

function isOnBoard(position) {
  return (
    position.row >= 0 &&
    position.row < BOARD_SIZE &&
    position.col >= 0 &&
    position.col < BOARD_SIZE
  );
}

function samePosition(a, b) {
  return a?.row === b?.row && a?.col === b?.col;
}

function toKey(position) {
  return `${position.row}:${position.col}`;
}

function opponent(player) {
  return player === RED ? BLACK : RED;
}

function capitalize(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function positionName(position) {
  const file = String.fromCharCode("A".charCodeAt(0) + position.col);
  return `${file}${BOARD_SIZE - position.row}`;
}

function describeSquare(row, col, piece, legalMove) {
  const parts = [positionName({ row, col })];
  if (piece) parts.push(`${piece.king ? "king " : ""}${piece.color} piece`);
  if (legalMove) parts.push(legalMove.capture ? "capture destination" : "legal destination");
  return parts.join(", ");
}

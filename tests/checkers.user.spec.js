const { test, expect } = require("@playwright/test");

test.describe("Checkers user scenarios", () => {
  test("initial load shows board, turn, and movable pieces", async ({ page }) => {
    await page.goto("/");

    await expect(page.locator("h1")).toHaveText("Checkers for Two");
    await expect(page.locator("#turnText")).toHaveText("Red");
    await expect(page.locator(".piece.red")).toHaveCount(12);
    await expect(page.locator(".piece.black")).toHaveCount(12);
    await expect(page.locator(".square.movable")).toHaveCount(4);
  });

  test("blocked piece guidance avoids false no-legal-moves error", async ({ page }) => {
    await page.goto("/");

    await page.click(".square[data-row='7'][data-col='0']");
    await expect(page.locator("#statusText")).toContainText(
      "That piece is blocked. Select a highlighted piece.",
    );
    await expect(page.locator("#statusText")).not.toContainText("no legal moves");
  });

  test("legal move changes turn and updates status", async ({ page }) => {
    await page.goto("/");

    await page.click(".square[data-row='5'][data-col='0']");
    await page.click(".square[data-row='4'][data-col='1']");
    await expect(page.locator("#turnText")).toHaveText("Black");
    await expect(page.locator("#statusText")).toContainText("Black");
  });

  test("mandatory capture restricts non-capturing pieces", async ({ page }) => {
    await page.goto("/");

    const board = await page.evaluate(() => {
      const b = window.__checkersTest.createEmptyBoard();
      b[5][2] = { color: "red", king: false };
      b[5][6] = { color: "red", king: false };
      b[4][3] = { color: "black", king: false };
      return b;
    });

    await page.evaluate((nextBoard) => {
      window.__checkersTest.setState({
        board: nextBoard,
        currentPlayer: "red",
        message: "Scenario: mandatory capture",
      });
    }, board);

    await expect(page.locator(".square.movable")).toHaveCount(1);
    await page.click(".square[data-row='5'][data-col='6']");
    await expect(page.locator("#statusText")).toContainText("A capture is required");
  });

  test("multi-jump keeps same player until jump chain ends", async ({ page }) => {
    await page.goto("/");

    const board = await page.evaluate(() => {
      const b = window.__checkersTest.createEmptyBoard();
      b[5][0] = { color: "red", king: false };
      b[4][1] = { color: "black", king: false };
      b[2][3] = { color: "black", king: false };
      b[0][7] = { color: "black", king: false };
      return b;
    });

    await page.evaluate((nextBoard) => {
      window.__checkersTest.setState({
        board: nextBoard,
        currentPlayer: "red",
        message: "Scenario: multi-jump",
      });
    }, board);

    await page.click(".square[data-row='5'][data-col='0']");
    await page.click(".square[data-row='3'][data-col='2']");
    await expect(page.locator("#turnText")).toHaveText("Red");
    await expect(page.locator("#statusText")).toContainText("continue jumping");

    await page.click(".square[data-row='1'][data-col='4']");
    await expect(page.locator("#turnText")).toHaveText("Black");
  });

  test("piece becomes king on reaching back rank", async ({ page }) => {
    await page.goto("/");

    const board = await page.evaluate(() => {
      const b = window.__checkersTest.createEmptyBoard();
      b[1][2] = { color: "red", king: false };
      return b;
    });

    await page.evaluate((nextBoard) => {
      window.__checkersTest.setState({
        board: nextBoard,
        currentPlayer: "red",
        message: "Scenario: kinging",
      });
    }, board);

    await page.click(".square[data-row='1'][data-col='2']");
    await page.click(".square[data-row='0'][data-col='1']");
    await expect(
      page.locator(".square[data-row='0'][data-col='1'] .piece.king"),
    ).toHaveCount(1);
  });

  test("undo and restart return game to expected states", async ({ page }) => {
    await page.goto("/");

    await page.click(".square[data-row='5'][data-col='0']");
    await page.click(".square[data-row='4'][data-col='1']");
    await expect(page.locator("#turnText")).toHaveText("Black");

    await page.click("#undoButton");
    await expect(page.locator("#turnText")).toHaveText("Red");

    await page.click("#restartButton");
    await expect(page.locator("#turnText")).toHaveText("Red");
    await expect(page.locator("#statusText")).toContainText("New game started");
    await expect(page.locator(".piece.red")).toHaveCount(12);
    await expect(page.locator(".piece.black")).toHaveCount(12);
  });
});

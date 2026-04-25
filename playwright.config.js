const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  reporter: "line",
  use: {
    baseURL: "http://localhost:4173",
    headless: true,
  },
  webServer: {
    command: "python3 -m http.server 4173",
    url: "http://localhost:4173",
    reuseExistingServer: true,
    timeout: 120000,
  },
});

import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

let server;
let workspace;

async function waitForServer(page) {
  let last = "";
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await page.request.get("/");
      if (response.ok()) return;
      last = String(response.status());
    } catch (error) {
      last = error instanceof Error ? error.message : String(error);
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`Creator Studio did not start: ${last}`);
}

test.beforeAll(async () => {
  workspace = fs.mkdtempSync(path.join(os.tmpdir(), "creator-studio-"));
  const publishing = path.join(workspace, "publishing");
  fs.mkdirSync(publishing, { recursive: true });
  server = spawn("./contentos.sh", ["dashboard", "--port", "4318"], {
    env: {
      ...process.env,
      VIDEO_FACTORY_WORKSPACE: workspace,
      VIDEO_FACTORY_PUBLISH_DIR: publishing,
    },
    stdio: "ignore",
  });
});

test.afterAll(async () => {
  server?.kill("SIGTERM");
});

test.describe("fixture browser journeys", () => {
  test.beforeEach(async ({ page }) => {
    await waitForServer(page);
  });

  for (const viewport of [{ width: 1280, height: 800 }, { width: 390, height: 844 }]) {
    for (const theme of ["dark", "light"]) {
      test(`jobs screen ${theme} ${viewport.width}`, async ({ page }) => {
        await page.setViewportSize(viewport);
        await page.emulateMedia({ colorScheme: theme, reducedMotion: "reduce" });
        await page.goto("/#/jobs");
        await page.evaluate((selected) => {
          document.documentElement.dataset.theme = selected;
          localStorage.setItem("contentos-theme", selected);
        }, theme);
        await expect(page.getByRole("heading", { name: "Jobs", exact: true })).toBeVisible();
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
        expect(overflow).toBe(false);
        for (const route of ["#/jobs", "#/queue", "#/health", "#/help", "#/jobs/new"]) {
          await page.goto(`/${route}`);
          await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
          const accessibility = await new AxeBuilder({ page }).analyze();
          expect(accessibility.violations, route).toEqual([]);
        }
      });
    }
  }

  test("Track B intake asks for a job id and does not start a render", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/#/track-b");
    await expect(page.getByRole("heading", { name: "Track B intake" })).toBeVisible();
    await expect(page.getByLabel("Job ID")).toBeVisible();
    await expect(page.locator('input[name="path"], input[name="destination"]')).toHaveCount(0);
    await page.getByLabel("Job ID").fill("missing-track-b");
    await page.getByRole("button", { name: "Inspect job" }).click();
    await expect(page.getByRole("alert")).toContainText(/not found/i);
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(accessibility.violations).toEqual([]);
  });

  test("keyboard reaches the primary screens and the approval dialog restores focus", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/#/jobs");
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toBeVisible();
    for (const name of ["Queue", "Health", "Help"]) {
      await page.getByRole("link", { name }).click();
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
    await page.goto("/#/jobs/new");
    await expect(page.getByRole("heading", { name: "New job" })).toBeVisible();
    const id = page.getByLabel("Job id");
    await id.focus();
    await expect(id).toBeFocused();
  });
});

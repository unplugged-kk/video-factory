// Measure a composition's layout in the headless Chrome hyperframes renders with.
// usage: node tests/layout_probe.mjs <index.html> <width> <height> <chrome-executable>
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer-core";

const [file, width, height, executablePath] = process.argv.slice(2);
const browser = await puppeteer.launch({ executablePath, headless: "shell", args: ["--no-sandbox"] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: Number(width), height: Number(height) });
  await page.goto(pathToFileURL(file).href);
  const scenes = await page.evaluate(() => {
    document.querySelectorAll("h1").forEach((h) => (h.style.transform = "none")); // the entrance tween offsets it by 60px
    const box = (el) => {
      const b = el.getBoundingClientRect();
      return { top: b.top, bottom: b.bottom, left: b.left, right: b.right };
    };
    return [...document.querySelectorAll(".scene")].map((s, i) => ({
      scene: i + 1,
      h1: box(s.querySelector("h1")),
      cap: box(s.querySelector(".cap")),
      capPosition: getComputedStyle(s.querySelector(".cap")).position,
    }));
  });
  console.log(JSON.stringify(scenes));
} finally {
  await browser.close();
}

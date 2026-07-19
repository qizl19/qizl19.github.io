const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(process.argv[2] || ".");
const output = path.resolve(process.argv[3] || "tmp/site-qa");
fs.mkdirSync(output, { recursive: true });

const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".pdf": "application/pdf",
};

const server = http.createServer((request, response) => {
  const url = new URL(request.url, "http://127.0.0.1");
  let relative = decodeURIComponent(url.pathname).replace(/^\/+/, "");
  if (!relative || relative.endsWith("/")) relative += "index.html";
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    response.writeHead(404);
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "Content-Type": mime[path.extname(file).toLowerCase()] || "application/octet-stream" });
  fs.createReadStream(file).pipe(response);
});

async function main() {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const origin = `http://127.0.0.1:${port}`;
  const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`page: ${error.message}`));
  page.on("requestfailed", (request) => errors.push(`request: ${request.url()} ${request.failure()?.errorText}`));

  await page.goto(`${origin}/aircraft/`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(output, "archive-desktop.png"), fullPage: true });
  await page.locator("#aircraft-search").fill("协和");
  if ((await page.locator('[data-aircraft-card]:visible').count()) !== 1) {
    throw new Error("Archive search filter did not return one card");
  }
  await page.locator("#aircraft-filters").evaluate((form) => form.reset());
  await page.waitForTimeout(50);

  await page.goto(`${origin}/aircraft/concorde/`, { waitUntil: "networkidle" });
  if ((await page.locator(".transcript-page").count()) !== 9) {
    throw new Error("Concorde transcript does not contain nine pages");
  }
  await page.screenshot({ path: path.join(output, "detail-desktop.png") });
  await page.locator("#gallery").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "detail-gallery.png") });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${origin}/aircraft/`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(output, "archive-mobile.png") });
  await page.goto(`${origin}/aircraft/y-20-kunpeng/`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(output, "detail-mobile.png") });

  await browser.close();
  if (errors.length) {
    throw new Error(errors.join("\n"));
  }
  console.log(`Browser QA passed; screenshots written to ${output}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(() => server.close());

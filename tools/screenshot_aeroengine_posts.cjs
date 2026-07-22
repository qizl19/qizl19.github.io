const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(process.argv[2] || ".");
const output = path.resolve(process.argv[3] || "tmp/aeroengine-posts-qa");
fs.mkdirSync(output, { recursive: true });
const posts = JSON.parse(fs.readFileSync(path.join(root, "data", "aeroengine_posts.json"), "utf8"));
const latest = posts[0];

const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".svg": "image/svg+xml; charset=utf-8",
  ".ico": "image/x-icon",
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

async function settle(page) {
  await page.waitForTimeout(600);
  await page.evaluate(() => {
    document.querySelector("#loading-box")?.remove();
    document.querySelectorAll("img[data-original]").forEach((image) => {
      image.src = image.dataset.original;
    });
  });
  await page.waitForTimeout(300);
}

async function assertArticle(page, label) {
  if ((await page.locator("#article-container > h2").count()) !== latest.headings.length) {
    throw new Error(`${label}: section count mismatch`);
  }
  if ((await page.locator("#card-toc .toc-item").count()) !== latest.headings.length) {
    throw new Error(`${label}: TOC count mismatch`);
  }
  for (const text of ["可复算的简化算例", "自测题", "答案与下一期衔接", "CC BY 4.0"]) {
    if ((await page.getByText(text, { exact: false }).count()) === 0) throw new Error(`${label}: missing ${text}`);
  }
  const broken = await page.locator("#article-container img").evaluateAll((images) =>
    images.filter((image) => image.complete && image.naturalWidth === 0)
      .map((image) => image.getAttribute("data-original") || image.src),
  );
  if (broken.length) throw new Error(`${label}: broken images: ${broken.join(", ")}`);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) throw new Error(`${label}: horizontal page overflow`);
}

async function main() {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const localErrors = [];
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (url.startsWith(origin) || url.startsWith("data:")) await route.continue();
    else await route.abort();
  });
  page.on("requestfailed", (request) => {
    if (request.url().startsWith(origin)) localErrors.push(`${request.url()} ${request.failure()?.errorText}`);
  });

  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded" });
  await settle(page);
  if ((await page.locator(`a[href="/p/${latest.postId}.html"]`).count()) === 0) throw new Error("Homepage missing latest aeroengine briefing");
  const background = await page.locator(".category-aeroengine").evaluate((element) => getComputedStyle(element).backgroundImage);
  if (!background.includes("aeroengine-brayton-cover.webp")) throw new Error("Aeroengine category card has no local cover");
  if ((await page.locator('script[src="/js/aircraft-article.js"]').count()) !== 0) throw new Error("Homepage loads heavy aircraft script");
  await page.screenshot({ path: path.join(output, "home-desktop.png"), fullPage: true });

  await page.goto(`${origin}/categories/${encodeURIComponent("航空发动机")}/`, { waitUntil: "domcontentloaded" });
  await settle(page);
  if ((await page.locator(`a[href="/p/${latest.postId}.html"]`).count()) === 0) throw new Error("Aeroengine category missing latest article");
  await page.screenshot({ path: path.join(output, "category-desktop.png"), fullPage: true });

  await page.goto(`${origin}/p/${latest.postId}.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await assertArticle(page, "desktop");
  await page.screenshot({ path: path.join(output, "article-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${origin}/p/${latest.postId}.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await assertArticle(page, "mobile");
  await page.screenshot({ path: path.join(output, "article-mobile.png"), fullPage: true });

  if (localErrors.length) throw new Error(`Local resource failures: ${localErrors.join(" | ")}`);
  await browser.close();
  server.close();
  console.log(`Browser validation passed: ${latest.postId}, desktop + 390px mobile`);
}

main().catch((error) => {
  server.close();
  console.error(error.stack || error);
  process.exitCode = 1;
});

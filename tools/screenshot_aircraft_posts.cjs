const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(process.argv[2] || ".");
const output = path.resolve(process.argv[3] || "tmp/aircraft-posts-qa");
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
  await page.waitForTimeout(900);
  await page.evaluate(() => {
    document.querySelector("#loading-box")?.remove();
    document.querySelectorAll("img[data-original]").forEach((image) => {
      image.src = image.dataset.original;
    });
  });
  await page.waitForTimeout(300);
}

async function main() {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const localErrors = [];
  page.on("requestfailed", (request) => {
    if (request.url().startsWith(origin)) localErrors.push(`request: ${request.url()} ${request.failure()?.errorText}`);
  });

  const postIds = ["eacebbb9", "6e9a9f42", "fe7680d9", "ebc40a24"];
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded" });
  await settle(page);
  if ((await page.getByText("飞机资料库", { exact: true }).count()) !== 0) {
    throw new Error("Homepage still shows the removed aircraft library");
  }
  for (const id of postIds) {
    if ((await page.locator(`a[href="/p/${id}.html"]`).count()) === 0) throw new Error(`Homepage missing ${id}`);
  }
  for (const title of ["直升机，不是直升飞机", "Hello World"]) {
    if ((await page.getByText(title, { exact: true }).count()) !== 0) throw new Error(`Homepage still lists removed article: ${title}`);
  }
  const aircraftBackground = await page.locator(".category-aircraft").evaluate((element) => getComputedStyle(element).backgroundImage);
  const weeklyBackground = await page.locator(".category-cad-cae").evaluate((element) => getComputedStyle(element).backgroundImage);
  if (!aircraftBackground.includes("y20-000.jpg")) throw new Error("Aircraft category does not use the local aircraft background");
  if (!weeklyBackground.includes("cad-cae-weekly-cover.svg")) throw new Error("CAD/CAE category does not use the local weekly cover");
  if ((await page.locator('a[href="/p/44bc590d.html"]').count()) === 0) throw new Error("Homepage missing CAD/CAE weekly article");
  await page.screenshot({ path: path.join(output, "home-desktop.png"), fullPage: true });

  await page.goto(`${origin}/categories/${encodeURIComponent("飞机资料整理")}/`, { waitUntil: "domcontentloaded" });
  await settle(page);
  for (const id of postIds) {
    if ((await page.locator(`a[href="/p/${id}.html"]`).count()) === 0) throw new Error(`Category missing ${id}`);
  }
  await page.screenshot({ path: path.join(output, "category-desktop.png"), fullPage: true });

  await page.goto(`${origin}/categories/CAD-CAE%E7%94%9F%E6%80%81%E5%91%A8%E6%8A%A5/`, { waitUntil: "domcontentloaded" });
  await settle(page);
  if ((await page.locator('a[href="/p/44bc590d.html"]').count()) === 0) throw new Error("CAD/CAE category missing first weekly article");
  await page.screenshot({ path: path.join(output, "weekly-category-desktop.png"), fullPage: true });

  for (const id of postIds) {
    await page.goto(`${origin}/p/${id}.html`, { waitUntil: "domcontentloaded" });
    await settle(page);
    if ((await page.locator("#article-container > h2").count()) !== 7) throw new Error(`${id} does not have seven sections`);
    if ((await page.locator("#card-toc .toc-item").count()) !== 7) throw new Error(`${id} TOC does not have seven entries`);
    if ((await page.getByText("全文转写", { exact: false }).count()) !== 0) throw new Error(`${id} contains transcript wording`);
    const broken = await page.locator("#article-container img").evaluateAll((images) =>
      images.filter((image) => image.complete && image.naturalWidth === 0).map((image) => image.getAttribute("data-original") || image.src),
    );
    if (broken.length) throw new Error(`${id} has broken article images: ${broken.join(", ")}`);
  }

  await page.goto(`${origin}/p/44bc590d.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  if ((await page.locator("#article-container > h2").count()) !== 11) throw new Error("CAD/CAE weekly article does not have eleven sections");
  if ((await page.locator("#card-toc .toc-item").count()) !== 11) throw new Error("CAD/CAE weekly TOC does not have eleven entries");
  if ((await page.getByText("全文转写", { exact: false }).count()) !== 0) throw new Error("CAD/CAE weekly article contains transcript wording");
  await page.screenshot({ path: path.join(output, "weekly-article-desktop.png"), fullPage: false });
  await page.locator("#本周态势总览").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "weekly-article-content.png"), fullPage: false });

  await page.goto(`${origin}/p/eacebbb9.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.screenshot({ path: path.join(output, "article-desktop.png"), fullPage: false });
  await page.locator("#基本资料").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "article-content.png"), fullPage: false });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${origin}/p/6e9a9f42.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.screenshot({ path: path.join(output, "article-mobile.png"), fullPage: false });
  await page.goto(`${origin}/p/44bc590d.html`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.screenshot({ path: path.join(output, "weekly-article-mobile.png"), fullPage: false });

  const removed = await page.request.get(`${origin}/aircraft/`);
  if (removed.status() !== 404) throw new Error(`/aircraft/ returned ${removed.status()}, expected 404`);
  for (const id of ["330e82f5", "4a17b156"]) {
    const removedPost = await page.request.get(`${origin}/p/${id}.html`);
    if (removedPost.status() !== 404) throw new Error(`/p/${id}.html returned ${removedPost.status()}, expected 404`);
  }
  await browser.close();
  if (localErrors.length) throw new Error(localErrors.join("\n"));
  console.log(`Blog browser QA passed; screenshots written to ${output}`);
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(() => server.close());

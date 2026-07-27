const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(process.argv[2] || ".");
const date = process.argv[3];
const output = path.resolve(process.argv[4] || `CAD-CAE-weekly-briefing-${date}.pdf`);
if (!date) throw new Error("Usage: build_cad_cae_weekly_pdf.cjs <root> <YYYY-MM-DD> <output.pdf>");

const posts = JSON.parse(fs.readFileSync(path.join(root, "data", "cad_cae_weekly_posts.json"), "utf8"));
const post = posts.find((item) => item.date === date);
if (!post) throw new Error(`No CAD/CAE weekly metadata for ${date}`);

const article = fs.readFileSync(path.join(root, post.contentFile), "utf8");
const coverPath = path.join(root, post.heroImage.replace(/^\/+/, ""));
const coverData = fs.readFileSync(coverPath).toString("base64");
const coverMime = path.extname(coverPath).toLowerCase() === ".webp" ? "image/webp" : "image/png";

const documentHtml = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${post.title}</title>
<style>
@page {
  size: A4;
  margin: 15mm 16mm 17mm;
  @bottom-center {
    content: "CAD/CAE 生态周报 · ${date}  ·  " counter(page) " / " counter(pages);
    color: #65758b;
    font-size: 8pt;
  }
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  margin: 0;
  color: #182433;
  font-family: "Microsoft YaHei", "Noto Sans CJK SC", "Segoe UI", sans-serif;
  font-size: 9.6pt;
  line-height: 1.72;
}
.cover {
  min-height: 260mm;
  margin: -15mm -16mm -17mm;
  padding: 24mm 20mm 18mm;
  color: #f2f7fb;
  background:
    linear-gradient(155deg, rgba(3, 11, 23, .22), rgba(3, 12, 24, .96)),
    url("data:${coverMime};base64,${coverData}") center/cover no-repeat;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  page-break-after: always;
}
.cover .kicker { color: #69d1ff; letter-spacing: .16em; font-weight: 700; }
.cover h1 { margin: 5mm 0 3mm; max-width: 155mm; font-size: 29pt; line-height: 1.18; }
.cover .subtitle { margin: 0; color: #cad8e6; font-size: 15pt; }
.cover .window { margin-top: 10mm; padding-top: 5mm; border-top: 1px solid rgba(255,255,255,.28); color: #aebfd0; font-size: 10pt; }
.cover .badge { display: inline-block; margin-top: 6mm; padding: 2mm 4mm; border: 1px solid rgba(105,209,255,.65); border-radius: 999px; color: #8edfff; }
.article > p:first-of-type,
.article > p:nth-of-type(2) { display: none; }
h2 {
  margin: 9mm 0 3mm;
  padding: 2.4mm 3.2mm;
  color: #0a3458;
  font-size: 17pt;
  line-height: 1.35;
  background: linear-gradient(90deg, #e7f4fb, #f7fbfd);
  border-left: 3.2mm solid #1e88c8;
  break-after: avoid;
}
h3 { margin: 6mm 0 2mm; color: #145b86; font-size: 12.5pt; break-after: avoid; }
p { margin: 0 0 3mm; text-align: justify; orphans: 3; widows: 3; }
blockquote {
  margin: 3mm 0 5mm;
  padding: 4mm 5mm;
  background: #eef7fb;
  border-left: 1.4mm solid #2b9ed8;
  color: #263d50;
  break-inside: avoid-page;
}
blockquote p:last-child { margin-bottom: 0; }
ol, ul { margin: 2mm 0 4mm; padding-left: 7mm; }
li { margin-bottom: 2mm; }
table {
  width: 100%;
  margin: 3mm 0 5mm;
  border-collapse: collapse;
  font-size: 8.1pt;
  line-height: 1.45;
  break-inside: avoid-page;
}
thead { display: table-header-group; }
tr { break-inside: avoid; }
th, td { padding: 2.2mm 2.4mm; border: .25mm solid #b8c8d5; vertical-align: top; }
th { color: #0d4064; background: #e9f3f8; text-align: left; }
code {
  padding: .2mm 1mm;
  border-radius: 1mm;
  background: #edf1f4;
  color: #8c2f39;
  font-family: Consolas, "Microsoft YaHei", monospace;
  font-size: .92em;
  overflow-wrap: anywhere;
}
a { color: #0b75b5; text-decoration: none; overflow-wrap: anywhere; }
strong { color: #112d43; }
.note {
  margin-top: 8mm;
  padding-top: 3mm;
  border-top: .25mm solid #b8c8d5;
  color: #607284;
  font-size: 8pt;
}
@media print {
  a[href^="http"]::after {
    content: "";
  }
}
</style>
</head>
<body>
<section class="cover">
  <div class="kicker">CAD / CAE ECOSYSTEM WEEKLY</div>
  <h1>${post.title}</h1>
  <p class="subtitle">${post.subtitle}</p>
  <p class="window">${post.window}</p>
  <span class="badge">FreeCAD · AI × CAD/CAE · VTK · CalculiX · Python/C++</span>
</section>
<main class="article">${article}</main>
<p class="note">本报告为截至 ${date} 09:00（Asia/Shanghai）的公开资料技术简报。开发提交、预印本与稳定发布已在正文中分开标注；所有 AI 结论均需在目标工作流中复算验证。</p>
</body>
</html>`;

async function main() {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ||
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 1 });
  await page.setContent(documentHtml, { waitUntil: "load" });
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: output,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: false,
  });
  await browser.close();
  console.log(`PDF generated: ${output}`);
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exit(1);
});

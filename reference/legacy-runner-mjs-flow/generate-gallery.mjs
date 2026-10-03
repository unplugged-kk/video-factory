// Build a review gallery of every rendered video, grouped by product.
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(ROOT, "output");
const THUMBS = path.join(ROOT, "thumbs");
const STATE = path.join(ROOT, "state");
fs.mkdirSync(THUMBS, { recursive: true });

const mp4s = fs.readdirSync(OUT).filter((f) => f.endsWith(".mp4")).sort();
const PRODUCTS = { cueedit: "CueEdit", buildcheap: "BuildCheap", sheetai: "SheetAI", magicslides: "MagicSlides" };

function meta(id) {
  let title = id, keyword = "";
  try { title = JSON.parse(fs.readFileSync(path.join(STATE, id + ".json"))).title || id; } catch {}
  for (const loc of ["done", "queue", "failed", "building"]) {
    const bp = path.join(ROOT, loc, id, "BRIEF.md");
    if (fs.existsSync(bp)) {
      const m = fs.readFileSync(bp, "utf8").match(/Target keyword:\**\s*`?([^`\n]+)`?/i);
      if (m) keyword = m[1].trim();
      break;
    }
  }
  return { title, keyword };
}

const cards = { cueedit: [], buildcheap: [], sheetai: [], magicslides: [], other: [] };
for (const f of mp4s) {
  const id = f.replace(/\.mp4$/, "");
  const prod = Object.keys(PRODUCTS).find((p) => id.startsWith(p)) || "other";
  const thumb = path.join(THUMBS, id + ".jpg");
  if (!fs.existsSync(thumb)) {
    try { execSync(`ffmpeg -y -i "${path.join(OUT, f)}" -vf "scale=320:-1" -frames:v 1 "${thumb}" -ss 00:00:04`, { stdio: "ignore" }); } catch {}
  }
  const fmt = id.endsWith("9x16") ? "9:16" : id.endsWith("16x9") ? "16:9" : "";
  const { title, keyword } = meta(id);
  cards[prod].push({ id, title, keyword, fmt });
}

const section = (key) => {
  const list = cards[key];
  if (!list.length) return "";
  return `<h2>${PRODUCTS[key] || "Other"} <span>${list.length}</span></h2>
  <div class="grid">` + list.map((c) => `
    <div class="card ${c.fmt === "9:16" ? "v" : "h"}">
      <div class="hd"><b>${c.fmt}</b> <span>${escapeHtml(c.keyword || c.id)}</span></div>
      <video controls preload="none" poster="/thumbs/${c.id}.jpg" src="/output/${c.id}.mp4"></video>
      <div class="ttl">${escapeHtml(c.title)}</div>
    </div>`).join("") + `</div>`;
};
function escapeHtml(x){return String(x).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

const total = mp4s.length;
const html = `<!doctype html><html><head><meta charset="utf-8"><title>Video Review — all ${total}</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
 body{background:#0f1115;color:#e7e9ee;font-family:Outfit,sans-serif;margin:0;padding:24px}
 h1{font-size:22px;margin:0 0 4px} .sub{color:#9aa2b1;margin-bottom:24px}
 h2{font-size:15px;text-transform:uppercase;letter-spacing:.5px;color:#9aa2b1;margin:28px 0 12px;border-top:1px solid #2a2f3a;padding-top:18px}
 h2 span{background:#1e222b;color:#6c8cff;border-radius:20px;padding:2px 10px;font-size:13px;margin-left:6px}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
 .card{background:#171a21;border:1px solid #2a2f3a;border-radius:10px;padding:10px}
 .hd{font-size:11px;color:#9aa2b1;display:flex;gap:8px;margin-bottom:6px}
 .hd b{color:#6c8cff}
 video{width:100%;border-radius:6px;background:#000;max-height:300px}
 .card.v video{max-height:360px;width:auto;max-width:100%;display:block;margin:0 auto}
 .ttl{font-size:12px;margin-top:6px;color:#c7ccd6}
</style></head><body>
<h1>Video Review — all ${total} rendered</h1>
<div class="sub">Every rendered video, grouped by product. Play through them — notice they all share the same template/story.</div>
${section("cueedit")}${section("buildcheap")}${section("sheetai")}${section("magicslides")}${section("other")}
</body></html>`;

fs.writeFileSync(path.join(ROOT, "gallery.html"), html);
console.log(`gallery.html built: ${total} videos (cueedit ${cards.cueedit.length}, buildcheap ${cards.buildcheap.length}, sheetai ${cards.sheetai.length}, magicslides ${cards.magicslides.length})`);

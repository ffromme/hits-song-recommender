"""Web UI sederhana untuk mencoba rekomendasi lagu (alternatif CLI 03_recommend.py, mis. untuk presentasi).

Pemakaian:  python scripts/05_web.py   lalu buka http://127.0.0.1:8000
Hanya bisa dibuka dari laptop ini (127.0.0.1). Riwayat putar (cooldown) berlaku selama server berjalan.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from hits_rec.config import COOLDOWN_N, LLM_MODEL
from hits_rec.pipeline import DEMO_COMMENTS, Recommender

HOST, PORT = "127.0.0.1", 8000
MAX_COMMENT = 500  # komentar TikTok pendek; tolak input raksasa

PAGE = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HITS Song Recommender</title>
<style>
  :root { --bg:#f6f5f2; --card:#fff; --text:#1d1d1f; --muted:#6b6b70; --line:#e4e2dd; --accent:#d9480f; --chip:#f0eee9; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#141416; --card:#1e1e21; --text:#ececee; --muted:#9a9aa0; --line:#2e2e33; --accent:#ff7a3d; --chip:#2a2a2f; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 system-ui, "Segoe UI", sans-serif; }
  main { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:1.5rem; margin:0 0 4px; }
  .sub { color:var(--muted); margin:0 0 20px; font-size:.9rem; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
  textarea { width:100%; min-height:80px; padding:12px; border-radius:10px; border:1px solid var(--line);
             background:var(--bg); color:var(--text); font:inherit; resize:vertical; }
  button { font:inherit; cursor:pointer; border:0; border-radius:10px; }
  #send { margin-top:10px; padding:10px 20px; background:var(--accent); color:#fff; font-weight:600; }
  #send:disabled { opacity:.6; cursor:wait; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
  .chip { padding:6px 12px; background:var(--chip); color:var(--text); font-size:.85rem; }
  .label { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; margin:12px 0 2px; }
  .song { font-size:1.35rem; font-weight:700; }
  .artist { color:var(--muted); }
  .host { font-size:1.05rem; border-left:3px solid var(--accent); padding-left:12px; margin:6px 0; }
  .badge { display:inline-block; padding:2px 10px; border-radius:99px; background:var(--chip); font-size:.8rem; margin-right:6px; }
  .warn { background:#f8d7a6; color:#5a3200; }
  .bar { display:flex; align-items:center; gap:8px; font-size:.85rem; margin:3px 0; }
  .bar span:first-child { width:70px; color:var(--muted); }
  .bar i { height:8px; border-radius:4px; background:var(--accent); min-width:2px; }
  .error { color:#c92a2a; }
  ol { padding-left:20px; margin:0; } li { margin:4px 0; }
  .hidden { display:none; }
</style>
</head>
<body>
<main>
  <h1>🎧 HITS Song Recommender</h1>
  <p class="sub">Ketik komentar seperti penonton live TikTok. Model LLM: __MODEL__ · cooldown __COOLDOWN__ lagu terakhir.</p>

  <div class="card">
    <label for="comment" class="label">Komentar penonton</label>
    <textarea id="comment" maxlength="__MAX__" placeholder="mis. lg excited bgt nungguin kakak pulang dr rantau 😆"></textarea>
    <button id="send">Rekomendasikan</button>
    <div class="label">Contoh komentar</div>
    <div class="chips" id="examples"></div>
  </div>

  <div class="card hidden" id="result" aria-live="polite"></div>

  <div class="card hidden" id="historyCard">
    <div class="label">Riwayat sesi ini</div>
    <ol id="history"></ol>
  </div>
</main>
<script>
const EXAMPLES = __EXAMPLES__;
const $ = (id) => document.getElementById(id);
// Semua teks dari penonton/LLM dipasang lewat textContent (bukan innerHTML) agar aman dari HTML berbahaya.
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

for (const text of EXAMPLES) {
  const b = el("button", "chip", text);
  b.onclick = () => { $("comment").value = text; send(); };
  $("examples").append(b);
}

async function send() {
  const comment = $("comment").value.trim();
  if (!comment) return;
  $("send").disabled = true; $("send").textContent = "Memproses...";
  const box = $("result"); box.classList.remove("hidden"); box.replaceChildren(el("div", "label", "Memproses komentar..."));
  try {
    const res = await fetch("/api/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comment }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    render(data);
  } catch (err) {
    box.replaceChildren(el("div", "error", "Gagal: " + err.message));
  } finally {
    $("send").disabled = false; $("send").textContent = "Rekomendasikan";
  }
}

function render(r) {
  const box = $("result"), rec = r.recommendation, intent = r.intent;
  box.replaceChildren();
  box.append(el("div", "label", "Komentar"), el("div", null, r.comment), el("div", "label", "Intent"));
  const tags = el("div");
  tags.append(el("span", "badge", intent ? intent.type : "-"));
  if (intent && intent.needs_moderation) tags.append(el("span", "badge warn", "⚠ perlu moderasi"));
  tags.append(el("span", null, r.note));
  box.append(tags);
  if (rec) {
    box.append(el("div", "label", "Lagu terpilih"), el("div", "song", rec.song.title), el("div", "artist", rec.song.artist + " · energi " + rec.song.energy + " · " + rec.song.moods.join(", ")));
    box.append(el("div", "label", "Kalimat penyiar"), el("div", "host", rec.host_line));
    box.append(el("div", "label", "Alasan (untuk tim radio)"), el("div", null, rec.reason + " (dari " + rec.candidates_considered.length + " kandidat)"));
  } else {
    box.append(el("div", "label", "Lagu terpilih"), el("div", null, "Tidak ada lagu yang diantrikan."));
  }
  box.append(el("div", "label", "Latensi"));
  const total = r.timings.total || 1;
  for (const [step, sec] of Object.entries(r.timings)) {
    const row = el("div", "bar"), bar = el("i");
    bar.style.width = (sec / total * 300) + "px";
    row.append(el("span", null, step), bar, el("span", null, sec.toFixed(2) + " s"));
    box.append(row);
  }
  $("historyCard").classList.remove("hidden");
  $("history").prepend(el("li", null, (rec ? rec.song.title + " — " + rec.song.artist : "(tanpa lagu)") + "  ←  " + r.comment));
}

$("send").onclick = send;
$("comment").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    recommender: Recommender  # diisi di main()

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send(status, "application/json", json.dumps({"error": message}).encode())

    def do_GET(self) -> None:
        if self.path != "/":
            return self._error(404, "tidak ditemukan")
        page = (PAGE.replace("__MODEL__", LLM_MODEL).replace("__COOLDOWN__", str(COOLDOWN_N))
                .replace("__MAX__", str(MAX_COMMENT)).replace("__EXAMPLES__", json.dumps(DEMO_COMMENTS)))
        self._send(200, "text/html; charset=utf-8", page.encode())

    def do_POST(self) -> None:
        if self.path != "/api/recommend":
            return self._error(404, "tidak ditemukan")
        # Wajib JSON: situs lain di browser tidak bisa diam-diam mengirim request ini (dan menghabiskan kuota LLM)
        if self.headers.get("Content-Type") != "application/json":
            return self._error(415, "Content-Type harus application/json")
        try:
            length = int(self.headers.get("Content-Length", 0))
            comment = json.loads(self.rfile.read(min(length, 10_000)))["comment"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            return self._error(400, "body harus JSON {\"comment\": \"...\"}")
        if not comment or len(comment) > MAX_COMMENT:
            return self._error(400, f"komentar harus 1–{MAX_COMMENT} karakter")
        result = self.recommender.recommend(comment)
        self._send(200, "application/json", result.model_dump_json().encode())

    def log_message(self, format, *args) -> None:  # log ringkas ke terminal
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")


def main() -> None:
    print("Memuat katalog & model embedding ...")
    Handler.recommender = Recommender()
    # ponytail: satu request diproses bergantian (HTTPServer, bukan threading): aman untuk Recommender yang
    # menyimpan riwayat di memori; cukup untuk demo, perlu antrean/lock bila dipakai banyak orang sekaligus.
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Siap: buka http://{HOST}:{PORT}  (Ctrl+C untuk berhenti)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

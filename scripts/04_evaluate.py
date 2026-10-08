"""Tahap 7: menjalankan semua request uji di data/eval/queries.yaml dan menulis outputs/eval_report.md.

Cache LLM dimatikan secara default agar latensi yang terukur adalah latensi nyata.
Pemakaian:
  python scripts/04_evaluate.py                # tanpa jeda (bisa kena batas token/menit Groq -> latensi melonjak)
  python scripts/04_evaluate.py --pause 16     # jeda 16 s antar-request agar tidak kena batas token/menit
  python scripts/04_evaluate.py --cache        # pakai cache LLM (gratis & cepat, tapi latensi tidak realistis)
"""
import argparse
import statistics
import time
from datetime import datetime

import yaml

from hits_rec import llm
from hits_rec.config import EVAL_QUERIES_PATH, LLM_MODEL, OUTPUTS_DIR
from hits_rec.pipeline import Recommender
from hits_rec.schemas import PipelineResult

STEPS = ["intent", "retrieval", "rerank", "total"]


def check(expect: dict, result: PipelineResult) -> list[str]:
    """Bandingkan hasil dengan ekspektasi. Kembalikan daftar kegagalan ([] = semua lolos)."""
    intent, rec = result.intent, result.recommendation
    song = rec.song if rec else None
    failures = []
    if "type" in expect and (intent is None or intent.type != expect["type"]):
        failures.append(f"type≠{expect['type']}")
    if expect.get("moderation") and not (intent and intent.needs_moderation):
        failures.append("moderasi tidak terdeteksi")
    if expect.get("no_song") and rec:
        failures.append("seharusnya tanpa lagu")
    for key, label in [("song", "title"), ("artist", "artist"), ("energy", "energy"), ("language", "language")]:
        if key in expect and (song is None or expect[key].lower() not in str(getattr(song, label)).lower()):
            failures.append(f"{key}≠{expect[key]}")
    if "not_song" in expect and song and song.title.lower() == expect["not_song"].lower():
        failures.append(f"terpilih {expect['not_song']} (seharusnya tidak)")
    return failures


def cell(text: str) -> str:
    """Rapikan teks agar aman di dalam tabel markdown."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def latency_summary(results: list[PipelineResult]) -> list[str]:
    lines = ["| langkah | n | rata-rata | median | maks |", "|---|---|---|---|---|"]
    for step in STEPS:
        values = [r.timings[step] for r in results if step in r.timings]
        if values:
            lines.append(f"| {step} | {len(values)} | {statistics.mean(values):.2f} s | "
                         f"{statistics.median(values):.2f} s | {max(values):.2f} s |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=0, help="jeda (detik) antar-request")
    parser.add_argument("--cache", action="store_true", help="pakai cache LLM")
    args = parser.parse_args()
    llm.cache_enabled = args.cache

    queries = yaml.safe_load(EVAL_QUERIES_PATH.read_text(encoding="utf-8"))
    start = time.perf_counter()
    recommender = Recommender()
    startup = time.perf_counter() - start
    print(f"{len(queries)} request uji, LLM {LLM_MODEL}, startup {startup:.1f} s, cache {'ON' if args.cache else 'OFF'}")

    rows, results, passed = [], [], 0
    for i, query in enumerate(queries, start=1):
        if i > 1 and args.pause:
            time.sleep(args.pause)
        result = recommender.recommend(query["comment"])
        results.append(result)
        failures = check(query.get("expect", {}), result)
        passed += not failures
        status = "✅" if not failures else "❌ " + ", ".join(failures)
        print(f"  {i:2}. {status}  {result.timings['total']:.2f}s  {query['comment'][:60]}")

        intent = result.intent
        detected = "-" if intent is None else intent.type + (" ⚠moderasi" if intent.needs_moderation else "")
        rec = result.recommendation
        t = result.timings
        rows.append("| " + " | ".join(cell(x) for x in [
            i, query["category"], query["comment"], f"{detected}<br>{result.note}",
            f"{rec.song.title} — {rec.song.artist}" if rec else "-",
            rec.reason if rec else "-", rec.host_line if rec else "-", status,
            " / ".join(f"{t[s]:.2f}" if s in t else "-" for s in STEPS), "",
        ]) + " |")

    report = [
        "# Laporan Evaluasi Rekomendasi Lagu",
        "",
        f"- Waktu: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Model LLM: `{LLM_MODEL}` | cache LLM: {'ON' if args.cache else 'OFF'} | jeda antar-request: {args.pause:g} s",
        f"- Startup (muat katalog + model embedding): {startup:.1f} s",
        f"- Cek otomatis lolos: **{passed}/{len(queries)}**",
        f"- Panggilan API LLM: {llm.stats['api_calls']} (retry JSON: {llm.stats['retries']}, "
        f"retry respons kosong: {llm.stats['empty_retries']}, dari cache: {llm.stats['cache_hits']})",
        "",
        "## Ringkasan latensi",
        "",
        *latency_summary(results),
        "",
        "`total` termasuk waktu menunggu bila batas token/menit provider tercapai.",
        "",
        "## Detail per request",
        "",
        "Latensi dalam detik: intent / retrieval / rerank / total. Isi kolom **nilai manual (1–5)** sendiri.",
        "",
        "| # | kategori | request | intent terdeteksi | lagu terpilih | alasan | host_line | cek otomatis | latensi (s) | nilai manual (1–5) |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    OUTPUTS_DIR.mkdir(exist_ok=True)
    path = OUTPUTS_DIR / "eval_report.md"
    path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nCek otomatis lolos {passed}/{len(queries)}. Laporan: {path}")
    print("\n".join(latency_summary(results)))


if __name__ == "__main__":
    main()

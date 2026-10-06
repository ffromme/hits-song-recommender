"""Tahap 2: melabeli mood lagu di katalog dengan LLM, lalu simpan ke data/labeled/songs_labeled.jsonl.

Inkremental: lagu yang sudah ada di songs_labeled.jsonl dilewati, jadi menambah lagu ke songs.csv
hanya melabeli lagu barunya. Untuk melabeli ulang semuanya, hapus songs_labeled.jsonl.
Pemakaian:  python scripts/01_label_catalog.py
"""
import time

from openai import RateLimitError

from hits_rec import llm
from hits_rec.catalog import load_catalog
from hits_rec.config import LABELED_PATH, LLM_MODEL, LOW_CONFIDENCE
from hits_rec.labeling import BATCH_SIZE, label_batch, load_labeled, save_labeled


def main() -> None:
    songs, problems = load_catalog()
    for problem in problems:
        print(f"[katalog] {problem}")

    done = {s.song_id: s for s in load_labeled()}
    todo = [s for s in songs if s.song_id not in done]
    print(f"Katalog {len(songs)} lagu: {len(songs) - len(todo)} sudah berlabel, {len(todo)} akan dilabeli "
          f"dengan {LLM_MODEL} ({BATCH_SIZE} lagu/request)")

    start = time.perf_counter()
    for i in range(0, len(todo), BATCH_SIZE):
        chunk = todo[i : i + BATCH_SIZE]
        try:
            for song in label_batch(chunk):
                done[song.song_id] = song
        except RateLimitError as err:
            print(f"  Kuota/rate limit LLM habis, berhenti. Jalankan ulang nanti untuk melanjutkan.\n  {str(err)[:200]}")
            break
        except Exception as err:  # satu batch gagal tidak menggagalkan batch lain
            print(f"  GAGAL batch {chunk[0].title} … {chunk[-1].title}: {err}")
        print(f"  {min(i + BATCH_SIZE, len(todo))}/{len(todo)} diproses ({time.perf_counter() - start:.0f} detik)")

    # Simpan mengikuti urutan katalog; lagu yang sudah dihapus dari songs.csv ikut terbuang
    labeled = [done[s.song_id] for s in songs if s.song_id in done]
    save_labeled(labeled)
    missing = [s for s in songs if s.song_id not in done]
    print(f"\nTersimpan {len(labeled)}/{len(songs)} lagu ke {LABELED_PATH}")
    print(f"Panggilan API: {llm.stats['api_calls']}, dari cache: {llm.stats['cache_hits']}, "
          f"retry JSON: {llm.stats['retries']}")
    if missing:
        print(f"Belum berlabel ({len(missing)}), jalankan ulang script: {', '.join(s.title for s in missing)}")

    print("\n=== 10 contoh hasil ===")
    for s in labeled[:: max(1, len(labeled) // 10)][:10]:
        print(f"\n{s.title} — {s.artist}  (confidence {s.confidence:.2f})")
        print(f"  {s.mood_description}")
        print(f"  moods: {', '.join(s.moods)} | energy: {s.energy} | valence: {s.valence}")
        print(f"  situasi: {'; '.join(s.suitable_situations)}")

    low = sorted((s for s in labeled if s.confidence < LOW_CONFIDENCE), key=lambda s: s.confidence)
    print(f"\n=== Confidence < {LOW_CONFIDENCE}: {len(low)} lagu, tinjau manual ===")
    for s in low:
        print(f"  {s.confidence:.2f}  {s.song_id}  {s.title} — {s.artist}")


if __name__ == "__main__":
    main()

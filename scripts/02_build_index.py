"""Tahap 3: membangun indeks vektor (ChromaDB) dari songs_labeled.jsonl, lalu menguji beberapa query.

Pemakaian:
  python scripts/02_build_index.py                       # bangun indeks + 3 query uji
  python scripts/02_build_index.py "lagi galau berat"    # bangun indeks + query sendiri
"""
import sys
import time

from hits_rec.config import CHROMA_DIR, EMBEDDING_MODEL
from hits_rec.index import build_index, search, song_document
from hits_rec.labeling import load_labeled

DEMO_QUERIES = [
    "lagi excited banget nunggu kakak pulang dari rantau",
    "baru putus, pengen nangis sendirian di kamar",
    "butuh semangat buat begadang ngerjain skripsi",
]


def main() -> None:
    songs = load_labeled()
    by_id = {s.song_id: s for s in songs}

    start = time.perf_counter()
    count = build_index(songs)
    print(f"Indeks dibangun: {count} lagu, model {EMBEDDING_MODEL}, {time.perf_counter() - start:.1f} detik")
    print(f"Lokasi: {CHROMA_DIR}")
    print(f"\nContoh teks yang di-embed ({songs[0].title}):\n  {song_document(songs[0])}")

    for query in sys.argv[1:] or DEMO_QUERIES:
        start = time.perf_counter()
        results = search(query, n=5)
        print(f"\nQuery: \"{query}\"  ({(time.perf_counter() - start) * 1000:.0f} ms)")
        for rank, (song_id, score) in enumerate(results, start=1):
            s = by_id[song_id]
            print(f"  {rank}. {score:.3f}  {s.title} — {s.artist}  [{s.energy}, {s.valence}] {', '.join(s.moods)}")


if __name__ == "__main__":
    main()

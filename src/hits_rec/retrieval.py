"""Retrieval: mencari kandidat lagu dari katalog berdasarkan Intent.

- Request eksplisit  -> `find_explicit`: fuzzy match judul/artis (toleran typo & beda ejaan).
- Request mood       -> `search_by_mood`: vector search + filter bahasa, cooldown, energi.
- `PlayHistory`      -> riwayat putar di memori, untuk cooldown.

Cooldown TIDAK diterapkan di `find_explicit`: kalau penonton minta lagu yang baru diputar, pipeline (Tahap 6)
yang memutuskan responsnya (mis. "barusan sudah diputar").

Jalankan `python -m hits_rec.retrieval` untuk demo.
"""
import re
from collections import deque
from difflib import SequenceMatcher
from functools import lru_cache

from hits_rec.catalog import normalize
from hits_rec.config import COOLDOWN_N, FUZZY_MIN_SCORE, TOP_K_CANDIDATES
from hits_rec.labeling import load_labeled
from hits_rec.schemas import Energy, LabeledSong

ENERGY_LEVEL = {"rendah": 0, "sedang": 1, "tinggi": 2}

# Pemisah nama artis kolaborasi: "Mark Ronson feat. Bruno Mars", "Bob Marley and The Wailers", "A, B", "A & B"
_ARTIST_SPLIT = re.compile(r"\s+(?:feat\.?|ft\.?|and|&|x|with)\s+|,\s*", re.IGNORECASE)


class PlayHistory:
    """Riwayat putar sederhana: hanya mengingat `size` song_id terakhir (yang lebih lama otomatis terbuang).

    ponytail: hanya di memori, hilang saat program ditutup; simpan ke file/DB bila perlu bertahan antar-sesi live.
    """

    def __init__(self, size: int = COOLDOWN_N):
        self._recent: deque[str] = deque(maxlen=size)

    def add(self, song_id: str) -> None:
        self._recent.append(song_id)

    def __contains__(self, song_id: str) -> bool:
        return song_id in self._recent

    def __len__(self) -> int:
        return len(self._recent)


@lru_cache(maxsize=1)
def catalog() -> dict[str, LabeledSong]:
    """Katalog berlabel, dimuat sekali. Hanya lagu berlabel yang bisa direkomendasikan."""
    return {s.song_id: s for s in load_labeled()}


def _match_key(text: str) -> str:
    """Bentuk pembanding: kata ulang ditulis lengkap ("hati2" -> "hati hati") dan spasi dibuang
    ("dijalan" == "di jalan", "dewa19" == "dewa 19")."""
    return re.sub(r"\b([^\W\d_]+)2\b", r"\1 \1", normalize(text)).replace(" ", "")


def _similarity(a: str, b: str) -> float:
    """Kemiripan dua teks, 0 (beda total) sampai 1 (sama), setelah dinormalisasi."""
    return SequenceMatcher(None, _match_key(a), _match_key(b)).ratio()


def _artist_similarity(query: str, artist: str) -> float:
    """Seperti _similarity, tapi "Bruno Mars" juga cocok dengan "Mark Ronson feat. Bruno Mars"."""
    parts = [artist, *_ARTIST_SPLIT.split(artist)]
    return max(_similarity(query, part) for part in parts if part)


def find_explicit(title: str | None, artist: str | None) -> list[tuple[LabeledSong, float]]:
    """Cari lagu yang judul dan/atau artisnya mirip. Kembalikan [(lagu, skor)] urut terbaik; [] bila tidak ada.

    Bila judul dan artis sama-sama diisi, keduanya harus cocok (judul sama tapi artis lain = lagu lain).
    Bila hanya artis, semua lagu artis itu dikembalikan.
    """
    results = []
    for song in catalog().values():
        scores = []
        if title:
            scores.append(_similarity(title, song.title))
        if artist:
            scores.append(_artist_similarity(artist, song.artist))
        if scores and min(scores) >= FUZZY_MIN_SCORE:
            results.append((song, sum(scores) / len(scores)))
    return sorted(results, key=lambda r: r[1], reverse=True)


def filter_energy(
    candidates: list[tuple[LabeledSong, float]], energy_hint: Energy | None
) -> list[tuple[LabeledSong, float]]:
    """Filter energi yang lunak: buang yang bertolak belakang (rendah vs tinggi), dahulukan yang energinya sama.

    Urutan kemiripan dipertahankan di dalam tiap kelompok energi.
    """
    if not energy_hint:
        return candidates
    target = ENERGY_LEVEL[energy_hint]
    kept = [c for c in candidates if abs(ENERGY_LEVEL[c[0].energy] - target) <= 1]
    return sorted(kept, key=lambda c: abs(ENERGY_LEVEL[c[0].energy] - target))


def search_by_mood(
    mood_profile: str,
    energy_hint: Energy | None = None,
    language_hint: str | None = None,
    history: PlayHistory | None = None,
    k: int = TOP_K_CANDIDATES,
) -> list[tuple[LabeledSong, float]]:
    """Vector search berdasarkan mood, lalu filter. Kembalikan maksimal `k` [(lagu, skor kemiripan)]."""
    # Diimpor di sini agar modul ini (dan test-nya) tidak ikut memuat model embedding bila hanya butuh fuzzy match
    from hits_rec.index import search

    history = history or PlayHistory(0)
    n = k + len(history)  # ambil lebih banyak untuk mengganti lagu yang terbuang karena cooldown
    where = {"language": language_hint} if language_hint else None
    hits = search(mood_profile, n=n, where=where)
    if not hits and where:  # bahasa itu tidak ada di katalog: abaikan filter bahasa
        hits = search(mood_profile, n=n)

    songs = catalog()
    candidates = [(songs[sid], score) for sid, score in hits if sid in songs and sid not in history]
    return filter_energy(candidates, energy_hint)[:k]


def _print(label: str, results: list[tuple[LabeledSong, float]], top: int = 5) -> None:
    print(f"\n{label}  -> {len(results)} hasil")
    for song, score in results[:top]:
        print(f"   {score:.3f}  {song.title} — {song.artist}  [{song.language}, {song.energy}, {song.valence}]")


if __name__ == "__main__":
    import time

    print("=== Request eksplisit (fuzzy match) ===")
    for title, artist in [
        ("Hati-hati di Jalan", "Tulus"),
        ("Separuh Napas", "Dewa19"),  # typo judul & artis
        (None, "Ed Sheeran"),  # hanya artis
        (None, "Bruno Mars"),  # artis kolaborasi ("Mark Ronson feat. Bruno Mars")
        ("Lathi", "Weird Genius"),  # tidak ada di katalog
    ]:
        start = time.perf_counter()
        results = find_explicit(title, artist)
        _print(f"title={title!r} artist={artist!r} ({(time.perf_counter() - start) * 1000:.1f} ms)", results)

    print("\n=== Request mood (vector search + filter) ===")
    excited = ("Lagu ceria dan penuh semangat yang menggambarkan kegembiraan dan ketidaksabaran menunggu kedatangan "
               "keluarga yang pulang dari rantau, cocok untuk momen reuni yang hangat dan bahagia.")
    start = time.perf_counter()
    search_by_mood(excited)  # pemanasan: memuat model embedding
    print(f"(memuat model embedding: {time.perf_counter() - start:.1f} s)")

    _print("excited, TANPA filter energi", search_by_mood(excited))
    start = time.perf_counter()
    results = search_by_mood(excited, energy_hint="tinggi")
    _print(f"excited, energy_hint=tinggi ({(time.perf_counter() - start) * 1000:.0f} ms)", results)

    history = PlayHistory()
    for song, _ in results[:3]:
        history.add(song.song_id)
    _print(f"excited, energy_hint=tinggi, cooldown {len(history)} lagu teratas tadi",
           search_by_mood(excited, energy_hint="tinggi", history=history))

    santai = "Lagu Indonesia yang santai dan menenangkan, cocok untuk menemani sore hari sambil menikmati secangkir kopi."
    _print("santai sore ngopi, language_hint=id, energy_hint=rendah",
           search_by_mood(santai, energy_hint="rendah", language_hint="id"))
    _print("santai sore ngopi, language_hint=ko (tidak ada di katalog -> filter bahasa diabaikan)",
           search_by_mood(santai, language_hint="ko"), top=3)

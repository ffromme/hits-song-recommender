"""Membaca, memvalidasi, dan membersihkan katalog lagu dari songs.csv.

Jalankan `python -m hits_rec.catalog` untuk melihat ringkasan katalog.
"""
import csv
import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from hits_rec.config import RAW_CATALOG_PATH
from hits_rec.schemas import Song

REQUIRED_COLUMNS = {"title", "artist", "language"}


def normalize(text: str) -> str:
    """Bentuk baku untuk perbandingan: huruf kecil, tanpa tanda baca, spasi tunggal.

    Contoh: 'Hati-Hati di Jalan' dan 'hati hati  di JALAN' sama-sama menjadi 'hati hati di jalan'.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def make_song_id(title: str, artist: str) -> str:
    """ID stabil: selalu sama untuk judul + artis yang sama, tidak bergantung urutan baris di CSV.

    Dibuat dari hash (sidik jari teks) judul dan artis yang sudah dinormalisasi.
    Konsekuensinya, kalau judul/artis diganti ejaannya (bukan sekadar huruf besar/tanda baca), ID ikut berubah.
    """
    key = f"{normalize(artist)}|{normalize(title)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def load_catalog(path: Path = RAW_CATALOG_PATH) -> tuple[list[Song], list[str]]:
    """Baca CSV, kembalikan (lagu valid tanpa duplikat, daftar masalah per baris).

    Baris yang tidak valid atau duplikat dilewati dan dicatat, bukan menghentikan program.
    Kolom wajib yang hilang di header langsung menjadi error.
    """
    # utf-8-sig: aman untuk CSV hasil "Save As" Excel yang diawali BOM
    with open(path, encoding="utf-8-sig", newline="") as f:
        header = f.readline()
        f.seek(0)
        # Excel berlokal Indonesia menyimpan CSV dengan pemisah ';', bukan ','
        delimiter = ";" if header.count(";") > header.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)

        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: kolom wajib tidak ada: {sorted(missing)}")

        songs: list[Song] = []
        problems: list[str] = []
        first_seen: dict[str, int] = {}  # song_id -> nomor baris pertama
        for line_no, row in enumerate(reader, start=2):  # baris 1 = header
            fields = {k: v for k, v in row.items() if k in Song.model_fields}  # kolom lain diabaikan
            song_id = make_song_id(row.get("title") or "", row.get("artist") or "")
            try:
                song = Song(song_id=song_id, **fields)
            except ValidationError as err:
                detail = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in err.errors())
                problems.append(f"baris {line_no}: tidak valid ({detail}), dilewati")
                continue
            if song_id in first_seen:
                problems.append(
                    f"baris {line_no}: duplikat dari baris {first_seen[song_id]} "
                    f"({song.title} - {song.artist}), dilewati"
                )
                continue
            first_seen[song_id] = line_no
            songs.append(song)
    return songs, problems


def _print_summary(songs: list[Song], problems: list[str]) -> None:
    print(f"Katalog: {RAW_CATALOG_PATH}")
    print(f"Lagu valid : {len(songs)}")
    print(f"Masalah    : {len(problems)}")
    for problem in problems:
        print(f"  - {problem}")
    print("Bahasa     :", dict(Counter(s.language for s in songs).most_common()))
    print("Genre      :", dict(Counter(s.genre or "(kosong)" for s in songs).most_common()))
    years = [s.year for s in songs if s.year]
    if years:
        print(f"Tahun      : {min(years)}–{max(years)} ({len(songs) - len(years)} tanpa tahun)")
    print("\nsong_id     judul — artis")
    for s in songs:
        print(f"{s.song_id}  {s.title} — {s.artist} [{s.language}]")


if __name__ == "__main__":
    _print_summary(*load_catalog())

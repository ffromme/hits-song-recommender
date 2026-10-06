"""Model data (pydantic) yang dipakai di seluruh modul.

Pydantic memeriksa tipe dan isi data saat objek dibuat. Kalau ada yang salah
(mis. tahun berupa teks), langsung muncul error yang jelas, tidak diam-diam lolos.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Energy = Literal["rendah", "sedang", "tinggi"]
Valence = Literal["negatif", "netral", "positif"]


class Song(BaseModel):
    """Satu lagu di katalog (dari songs.csv)."""

    song_id: str
    title: str = Field(min_length=1)
    artist: str = Field(min_length=1)
    language: str = Field(pattern=r"^[a-z]{2,3}$")  # kode ISO 639, mis. id, en, ko, jv
    genre: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)

    @field_validator("*", mode="before")
    @classmethod
    def _clean_text(cls, value):
        # Rapikan spasi; sel CSV yang kosong dianggap "tidak diisi" (None)
        if isinstance(value, str):
            value = " ".join(value.split())
            return value or None
        return value

    @field_validator("language", mode="before")
    @classmethod
    def _lowercase_language(cls, value):
        return value.lower() if isinstance(value, str) else value


class MoodLabel(BaseModel):
    """Label mood satu lagu hasil LLM (Tahap 2). Dipisah agar bisa dipakai untuk memvalidasi output LLM."""

    mood_description: str = Field(min_length=1)  # 1–2 kalimat, bahasa Indonesia
    moods: list[str]  # mis. senang, rindu, galau, semangat, tenang
    energy: Energy
    valence: Valence
    suitable_situations: list[str]  # mis. menyambut seseorang, belajar, patah hati
    confidence: float = Field(ge=0, le=1)  # rendah jika LLM tidak yakin mengenali lagunya


class LabeledSong(Song, MoodLabel):
    """Lagu + label mood. Satu baris di songs_labeled.jsonl."""


class Intent(BaseModel):
    """Maksud dari satu komentar pendengar (Tahap 4)."""

    type: Literal["explicit_song", "mood_request", "not_a_request"]
    # untuk explicit_song
    title: str | None = None
    artist: str | None = None
    # untuk mood_request
    mood_profile: str | None = None  # kalimat yang di-embed untuk pencarian
    energy_hint: Energy | None = None
    language_hint: str | None = None
    needs_moderation: bool = False  # true bila komentar tidak pantas


class Recommendation(BaseModel):
    """Hasil akhir pipeline (Tahap 6)."""

    song: LabeledSong
    reason: str
    host_line: str  # 1–2 kalimat gaya penyiar, tanpa mengutip lirik
    candidates_considered: list[str]  # song_id kandidat yang dipertimbangkan

"""Pelabelan mood: LLM membuat deskripsi mood + tag terstruktur untuk tiap lagu.

Input ke LLM hanya judul, artis, dan metadata CSV. Lirik tidak pernah diminta, disalin, atau disimpan.
Beberapa lagu dikirim sekaligus dalam satu request (batch) agar hemat kuota free tier
(Gemini gratis: 20 request/hari/model).
"""
import json
from pathlib import Path

from pydantic import BaseModel

from hits_rec.config import LABELED_PATH
from hits_rec.llm import complete_json
from hits_rec.schemas import LabeledSong, MoodLabel, Song

BATCH_SIZE = 20  # lagu per request LLM

# Kosakata mood yang disarankan. Tag yang seragam memudahkan pencarian di tahap berikutnya.
SUGGESTED_MOODS = [
    "senang", "semangat", "percaya diri", "santai", "tenang", "romantis", "bersyukur", "harapan",
    "rindu", "nostalgia", "haru", "sedih", "galau", "patah hati", "kesepian", "marah", "gelisah",
]

SYSTEM_PROMPT = f"""Kamu kurator musik untuk radio kampus di Indonesia.
Kamu akan menerima daftar lagu (JSON) berisi nomor, judul, artis, dan metadata.
Untuk SETIAP lagu, deskripsikan mood dan situasi yang cocok.

Aturan:
- Gunakan pengetahuanmu tentang lagu tersebut (tema, nuansa musik, tempo). JANGAN mengutip atau menyalin lirik sama sekali.
- Jika kamu tidak yakin mengenali sebuah lagu, JANGAN mengarang tema. Beri confidence di bawah 0.5 dan tulis
  deskripsi umum yang hanya berdasarkan genre/metadata, sebutkan bahwa kamu tidak yakin.
- confidence: 0.9–1.0 = sangat kenal lagunya; 0.6–0.89 = kenal tapi ragu pada sebagian detail; < 0.6 = tidak yakin.
- mood_description: 1–2 kalimat natural dalam bahasa Indonesia tentang perasaan yang dibawa lagu.
- moods: 2–5 tag huruf kecil. Utamakan dari daftar ini: {", ".join(SUGGESTED_MOODS)}. Boleh tag lain bila benar-benar perlu.
- energy: "rendah" | "sedang" | "tinggi" (tempo dan intensitas musik).
- valence: "negatif" | "netral" | "positif" (perasaan keseluruhan).
- suitable_situations: 2–5 frasa pendek bahasa Indonesia, mis. "menyambut seseorang pulang", "belajar malam", "patah hati".

Jawab HANYA dengan satu objek JSON, tanpa teks lain, berisi satu entri per lagu dengan nomor yang sama:
{{"labels": [{{"no": 1, "mood_description": "...", "moods": ["..."], "energy": "...", "valence": "...", "suitable_situations": ["..."], "confidence": 0.0}}]}}"""


class _NumberedLabel(MoodLabel):
    no: int  # nomor urut lagu di request, untuk mencocokkan jawaban dengan lagunya


class _LabelBatch(BaseModel):
    labels: list[_NumberedLabel]


def label_batch(songs: list[Song]) -> list[LabeledSong]:
    """Labeli beberapa lagu dalam satu panggilan LLM.

    Lagu yang tidak dijawab LLM tidak ikut dikembalikan; script akan mencobanya lagi saat dijalankan ulang.
    """
    items = [
        {"no": i, "judul": s.title, "artis": s.artist, "bahasa": s.language, "genre": s.genre, "tahun": s.year}
        for i, s in enumerate(songs, start=1)
    ]
    batch = complete_json(SYSTEM_PROMPT, json.dumps(items, ensure_ascii=False), _LabelBatch)
    by_no = {label.no: label for label in batch.labels}
    return [
        LabeledSong(**song.model_dump(), **by_no[i].model_dump(exclude={"no"}))
        for i, song in enumerate(songs, start=1)
        if i in by_no
    ]


def save_labeled(songs: list[LabeledSong], path: Path = LABELED_PATH) -> None:
    """Simpan ke JSONL: satu lagu per baris dalam format JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for song in songs:
            f.write(song.model_dump_json() + "\n")


def load_labeled(path: Path = LABELED_PATH) -> list[LabeledSong]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [LabeledSong.model_validate_json(line) for line in f if line.strip()]

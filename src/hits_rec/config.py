"""Konfigurasi terpusat: membaca .env, menyimpan path file data, dan konstanta."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Root proyek = dua tingkat di atas folder src/hits_rec/
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
RAW_CATALOG_PATH = DATA_DIR / "raw" / "songs.csv"
LABELED_PATH = DATA_DIR / "labeled" / "songs_labeled.jsonl"
EVAL_QUERIES_PATH = DATA_DIR / "eval" / "queries.yaml"
OUTPUTS_DIR = ROOT_DIR / "outputs"
LLM_CACHE_DIR = ROOT_DIR / ".cache" / "llm"  # cache jawaban LLM (di-ignore git, aman dihapus)
CHROMA_DIR = ROOT_DIR / ".cache" / "chroma"  # indeks vektor; dibuat ulang oleh scripts/02_build_index.py

# Lagu dengan confidence di bawah ini perlu ditinjau manual (LLM kurang yakin mengenali lagunya)
LOW_CONFIDENCE = 0.6

# LLM lewat API "OpenAI-compatible": Gemini, OpenRouter, Groq, dll. cukup ganti 3 nilai ini di .env.
# Rahasia hanya dari .env, tidak pernah ditulis di kode.
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash")
# Opsional: seberapa lama model "berpikir" sebelum menjawab (mis. low). Lebih rendah = lebih cepat. Kosong = default model.
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT") or None

# Model embedding multibahasa (mendukung Bahasa Indonesia)
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# Retrieval
TOP_K_CANDIDATES = 15  # jumlah kandidat dari vector search untuk request mood
COOLDOWN_N = 10  # lagu yang diputar dalam N lagu terakhir tidak direkomendasikan lagi
FUZZY_MIN_SCORE = 0.8  # kemiripan minimal (0–1) judul/artis untuk dianggap cocok pada request eksplisit

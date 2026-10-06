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

# LLM lewat API "OpenAI-compatible": Gemini, OpenRouter, Groq, dll. cukup ganti 3 nilai ini di .env.
# Rahasia hanya dari .env, tidak pernah ditulis di kode.
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")

# Model embedding multibahasa (mendukung Bahasa Indonesia)
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

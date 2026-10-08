"""Teks -> embedding.

Embedding = daftar angka (di model ini 384 angka) yang mewakili MAKNA sebuah teks. Dua teks yang artinya
mirip menghasilkan angka yang berdekatan, walaupun kata-katanya berbeda. Misalnya "kangen kakak yang
merantau" dekat dengan "rindu seseorang yang jauh".

Model e5 dilatih dengan awalan khusus: "query: " untuk teks pencarian (komentar pendengar) dan
"passage: " untuk dokumen yang dicari (deskripsi lagu). Tanpa awalan ini hasil pencariannya lebih buruk.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from hits_rec.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # Dimuat sekali saja (±2–5 detik). Unduhan pertama ±470 MB, lalu tersimpan di cache HuggingFace.
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embedding untuk dokumen (deskripsi lagu) yang disimpan di indeks."""
    vectors = _model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Embedding untuk teks pencarian (mood/permintaan pendengar)."""
    return _model().encode(f"query: {text}", normalize_embeddings=True).tolist()

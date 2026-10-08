"""Menyimpan dan mencari embedding lagu di ChromaDB.

ChromaDB adalah "vector database": tempat menyimpan embedding beserta data pendampingnya, yang bisa
dicari dengan pertanyaan "lagu mana yang embedding-nya paling dekat dengan embedding komentar ini?".
Berjalan lokal sebagai file di .cache/chroma/, tanpa server.

Per lagu disimpan:
- id        : song_id
- embedding : 384 angka hasil embed `song_document(song)`
- document  : teks yang di-embed (untuk dibaca manusia saat debug)
- metadata  : title, artist, language, energy, valence, confidence (untuk filter di Tahap 5)
"""
import chromadb
from chromadb.config import Settings

from hits_rec.config import CHROMA_DIR
from hits_rec.embedding import embed_passages, embed_query
from hits_rec.schemas import LabeledSong

COLLECTION = "songs"


def song_document(song: LabeledSong) -> str:
    """Gabungan teks mood yang di-embed. Judul/artis sengaja tidak ikut: pencarian ini berdasarkan mood."""
    return (
        f"{song.mood_description} Mood: {', '.join(song.moods)}. "
        f"Cocok untuk: {', '.join(song.suitable_situations)}."
    )


def _client() -> chromadb.ClientAPI:
    # anonymized_telemetry=False: jangan kirim statistik pemakaian ke server Chroma
    return chromadb.PersistentClient(path=str(CHROMA_DIR), settings=Settings(anonymized_telemetry=False))


def build_index(songs: list[LabeledSong]) -> int:
    """Bangun ulang indeks dari nol (cepat untuk ratusan–ribuan lagu). Kembalikan jumlah lagu tersimpan."""
    client = _client()
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    # cosine: ukur kemiripan dari arah vektor; skor kemiripan = 1 - jarak
    collection = client.create_collection(COLLECTION, configuration={"hnsw": {"space": "cosine"}})
    documents = [song_document(s) for s in songs]
    collection.add(
        ids=[s.song_id for s in songs],
        embeddings=embed_passages(documents),
        documents=documents,
        metadatas=[
            {"title": s.title, "artist": s.artist, "language": s.language,
             "energy": s.energy, "valence": s.valence, "confidence": s.confidence}
            for s in songs
        ],
    )
    return collection.count()


def search(query: str, n: int = 5, where: dict | None = None) -> list[tuple[str, float]]:
    """Cari lagu yang mood-nya paling mirip dengan `query`. Kembalikan [(song_id, skor 0–1), ...] urut terbaik.

    `where` = filter metadata ChromaDB, mis. {"language": "id"} (dipakai di Tahap 5).
    """
    result = _client().get_collection(COLLECTION).query(
        query_embeddings=[embed_query(query)], n_results=n, where=where
    )
    return [(song_id, 1 - dist) for song_id, dist in zip(result["ids"][0], result["distances"][0])]

"""Test rerank tanpa memanggil API: jawaban LLM dipalsukan."""
from hits_rec import rerank
from hits_rec.schemas import LabeledSong


def make_song(song_id):
    return LabeledSong(song_id=song_id, title=song_id.upper(), artist="x", language="id", mood_description="x",
                       moods=["senang"], energy="sedang", valence="positif", suitable_situations=["x"], confidence=1)


SONGS = [make_song("a"), make_song("b")]


def test_rerank_uses_llm_choice(monkeypatch):
    monkeypatch.setattr(rerank, "complete_json",
                        lambda system, user, schema: schema(choice=2, reason="cocok", host_line="Ini dia B!"))
    rec = rerank.rerank("komentar", "situasi", SONGS)
    assert rec.song.song_id == "b" and rec.host_line == "Ini dia B!" and rec.candidates_considered == ["a", "b"]


def test_rerank_falls_back_to_first_candidate(monkeypatch):
    # LLM memilih nomor di luar daftar -> kandidat pertama + kalimat host bawaan
    monkeypatch.setattr(rerank, "complete_json",
                        lambda system, user, schema: schema(choice=9, reason="?", host_line="?"))
    rec = rerank.rerank("komentar", "situasi", SONGS)
    assert rec.song.song_id == "a" and "A" in rec.host_line and rec.reason.startswith("Fallback")

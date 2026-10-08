"""Test retrieval tanpa model embedding: fuzzy match (pakai songs_labeled.jsonl asli), cooldown, filter energi."""
from hits_rec.retrieval import PlayHistory, filter_energy, find_explicit
from hits_rec.schemas import LabeledSong


def titles(results):
    return [song.title for song, _ in results]


def test_find_explicit_tolerates_typos():
    assert titles(find_explicit("separuh napas", "dewa19"))[0] == "Separuh Nafas"
    assert titles(find_explicit("hati hati dijalan", None))[0] == "Hati-Hati di Jalan"


def test_find_explicit_artist_only_matches_collaborations():
    assert set(titles(find_explicit(None, "Bruno Mars"))) == {"Count on Me", "Uptown Funk"}


def test_find_explicit_requires_both_title_and_artist_to_match():
    assert find_explicit("Kangen", "Tulus") == []  # judul ada, tapi artisnya lain
    assert find_explicit("Lathi", "Weird Genius") == []  # tidak ada di katalog


def test_play_history_forgets_oldest():
    history = PlayHistory(size=2)
    for song_id in ["a", "b", "c"]:
        history.add(song_id)
    assert "a" not in history and "b" in history and "c" in history


def make_song(song_id, energy):
    return LabeledSong(song_id=song_id, title=song_id, artist="x", language="id", mood_description="x",
                       moods=["senang"], energy=energy, valence="positif", suitable_situations=["x"], confidence=1)


def test_filter_energy_drops_opposite_and_prefers_exact():
    candidates = [(make_song("low", "rendah"), 0.9), (make_song("mid", "sedang"), 0.8), (make_song("high", "tinggi"), 0.7)]
    assert [s.song_id for s, _ in filter_energy(candidates, "tinggi")] == ["high", "mid"]
    assert filter_energy(candidates, None) == candidates

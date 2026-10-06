"""Test label_batch tanpa memanggil API: jawaban LLM dipalsukan."""
from hits_rec import labeling
from hits_rec.schemas import Song


def test_label_batch_matches_by_number_and_skips_missing(monkeypatch):
    songs = [
        Song(song_id="a", title="Kangen", artist="Dewa 19", language="id"),
        Song(song_id="b", title="Happy", artist="Pharrell Williams", language="en"),
        Song(song_id="c", title="Fix You", artist="Coldplay", language="en"),
    ]
    label = {"mood_description": "x", "moods": ["senang"], "energy": "tinggi", "valence": "positif",
             "suitable_situations": ["pagi"], "confidence": 0.9}

    def fake_complete_json(system, user, schema):
        # LLM menjawab urutan terbalik dan melewatkan lagu nomor 2
        return schema(labels=[{"no": 3, **label, "energy": "rendah"}, {"no": 1, **label}])

    monkeypatch.setattr(labeling, "complete_json", fake_complete_json)
    result = labeling.label_batch(songs)
    assert [(s.song_id, s.energy) for s in result] == [("a", "tinggi"), ("c", "rendah")]

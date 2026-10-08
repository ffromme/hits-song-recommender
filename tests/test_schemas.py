"""Test validasi model data: nilai di luar pilihan yang sah harus ditolak."""
import pytest
from pydantic import ValidationError

from hits_rec.schemas import Intent, MoodLabel

LABEL = {"mood_description": "x", "moods": ["senang"], "energy": "tinggi", "valence": "positif",
         "suitable_situations": ["x"], "confidence": 0.9}


def test_intent_defaults_and_rejects_unknown_values():
    intent = Intent(type="mood_request", mood_profile="lagu ceria")
    assert intent.needs_moderation is False and intent.title is None
    with pytest.raises(ValidationError):
        Intent(type="lagu_please")
    with pytest.raises(ValidationError):
        Intent(type="mood_request", energy_hint="super")


def test_mood_label_rejects_bad_energy_and_confidence():
    assert MoodLabel(**LABEL).energy == "tinggi"
    with pytest.raises(ValidationError):
        MoodLabel(**{**LABEL, "energy": "high"})  # harus bahasa Indonesia: rendah/sedang/tinggi
    with pytest.raises(ValidationError):
        MoodLabel(**{**LABEL, "confidence": 1.5})  # confidence 0–1

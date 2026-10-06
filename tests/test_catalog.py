"""Test kecil untuk catalog.py dan validasi Song."""
import pytest

from hits_rec.catalog import load_catalog, make_song_id


def write_csv(tmp_path, text):
    path = tmp_path / "songs.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_song_id_ignores_case_spacing_and_punctuation():
    assert make_song_id("Hati-Hati di Jalan", "Tulus") == make_song_id(" hati hati  di JALAN", "TULUS")
    assert make_song_id("Kangen", "Dewa 19") != make_song_id("Kangen", "Tulus")


def test_load_catalog_dedupes_and_reports_invalid_rows(tmp_path):
    path = write_csv(
        tmp_path,
        "title,artist,language,genre,year\n"
        "Kangen,Dewa 19,id,pop rock,1992\n"
        "kangen,DEWA 19,ID,,\n"  # duplikat (beda huruf besar)
        "Happy,Pharrell Williams,English,pop,2013\n"  # bahasa bukan kode ISO
        ",Tanpa Judul,id,,\n"  # judul kosong
        "Fix You,Coldplay,en,,tahun lalu\n",  # tahun bukan angka
    )
    songs, problems = load_catalog(path)
    assert [s.title for s in songs] == ["Kangen"]
    assert songs[0].year == 1992
    assert len(problems) == 4
    assert "duplikat dari baris 2" in problems[0]


def test_load_catalog_accepts_semicolon_and_empty_optional_fields(tmp_path):
    path = write_csv(tmp_path, "﻿title;artist;language;genre;year\nBertaut;Nadin Amizah; ID ;;\n")
    songs, problems = load_catalog(path)
    assert problems == []
    assert songs[0].language == "id" and songs[0].genre is None and songs[0].year is None


def test_load_catalog_missing_required_column(tmp_path):
    with pytest.raises(ValueError, match="language"):
        load_catalog(write_csv(tmp_path, "title,artist\nKangen,Dewa 19\n"))

# CLAUDE.md: hits-song-recommender

## Ringkasan proyek
Pemilik: Iam, mahasiswa Informatika yang sedang kerja praktek di HITS UNIKOM RADIO (media kampus).
Proyek besarnya adalah agent AI penyiar radio untuk live TikTok. Repo ini **hanya** memuat prototipe
**modul rekomendasi lagu**: komentar pendengar (eksplisit "putar lagu X" atau implisit berbasis mood/situasi)
diubah menjadi 1 lagu dari katalog, ditambah kalimat host.

Alur: komentar → `intent` (LLM) → `retrieval` (fuzzy match atau vector search + filter) → `rerank` (LLM pilih 1 + host_line) → `Recommendation`.

## Scope
- Di dalam scope: library Python `src/hits_rec/` + script CLI di `scripts/`.
- Di luar scope: TikTok, avatar 3D, TTS, dialog 2 agent, pemutar audio.
- Jangan mengunduh/memutar audio. Jangan menyalin atau menyimpan lirik berhak cipta.

## Aturan kerja
1. Kerjakan **per tahap**. Setelah tiap tahap: jalankan, tunjukkan output nyata, ringkas 3–5 kalimat, lalu **berhenti dan tunggu "lanjut"**.
2. Tanpa Jupyter notebook; hanya modul `.py` dan script terminal.
3. Jangan instal paket besar (mis. PyTorch GPU) tanpa memberi tahu dulu.
4. Keputusan desain yang punya beberapa opsi sama-masuk-akal: tanya singkat dulu. Kalau jelas: putuskan dan sebutkan alasannya.
5. Rahasia hanya di `.env` (di-ignore git). Template ada di `.env.example`.
6. Komentar kode & README berbahasa Indonesia; nama variabel/fungsi berbahasa Inggris.
7. Jelaskan istilah teknis (embedding, vector DB, dsb.) dengan bahasa sederhana karena pemilik masih awam.
8. Jangan mengubah struktur direktori tanpa bertanya.

## Tahapan
0. Scaffolding (selesai)
1. Skema & katalog: `schemas.py`, `catalog.py` (selesai)
2. Pelabelan mood: `llm.py`, `labeling.py`, `scripts/01_label_catalog.py` (selesai)
3. Embedding & indeks: `embedding.py`, `index.py`, `scripts/02_build_index.py`
4. Intent: `intent.py`
5. Retrieval & filter (fuzzy match, vector search, cooldown): `retrieval.py`
6. Rerank & host_line: `rerank.py`, `pipeline.py`
7. CLI & evaluasi: `scripts/03_recommend.py`, `scripts/04_evaluate.py`, `data/eval/queries.yaml`
8. Rapikan: README, tests, update file ini

## Struktur direktori
```
hits-song-recommender/
├── CLAUDE.md, README.md, requirements.txt, pyproject.toml, .env.example, .gitignore
├── data/raw/songs.csv                  # katalog mentah: title, artist, language (+ genre, year)
├── data/labeled/songs_labeled.jsonl    # hasil pelabelan mood oleh LLM
├── data/eval/queries.yaml              # request uji + ekspektasi
├── src/hits_rec/                       # config, schemas, llm, catalog, labeling, embedding, index,
│                                       # intent, retrieval, rerank, pipeline
├── scripts/                            # 01_label_catalog, 02_build_index, 03_recommend, 04_evaluate
├── outputs/                            # laporan evaluasi, log
└── tests/
```
`pyproject.toml` ditambahkan (disetujui) agar paket bisa diinstal editable (`pip install -e .`).

## Keputusan teknis
- Python 3.14 (venv `.venv`). 3.10 juga terpasang tapi end-of-life Oktober 2026; semua dependensi tersedia untuk 3.14.
- GPU: RTX 3050 6GB tersedia, tapi dipakai **PyTorch CPU**. Model embedding kecil cukup cepat di CPU untuk katalog ratusan sampai ribuan lagu, dan versi GPU berukuran ±2,5 GB.
- Embedding: `intfloat/multilingual-e5-small` (bukan `paraphrase-multilingual-MiniLM-L12-v2`), karena dilatih khusus untuk pencarian kalimat pendek → dokumen. Wajib awalan `query: ` / `passage: `.
- Vector DB: ChromaDB lokal.
- LLM: provider gratis lewat API OpenAI-compatible (paket `openai`), dibungkus `llm.py`. Diatur dari `.env`:
  `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`. Default Gemini `gemini-3.5-flash`. **Free tier Gemini = 20 request/hari PER MODEL** (kuota tiap model terpisah;
  3.7/3.8 sering 503 "high demand"). Karena itu pelabelan di-batch 20 lagu/request. Alternatif Groq/OpenRouter
  ada di `.env.example`. Output JSON diminta lewat prompt lalu divalidasi pydantic + retry, supaya jalan di semua provider.
  Catatan: data free tier Gemini dipakai Google untuk melatih model.
- Cache LLM: `.cache/llm/<sha256>.json` (kunci = model + prompt + nama schema). Aman dihapus.
- Pelabelan inkremental: lagu yang sudah ada di `songs_labeled.jsonl` dilewati; hapus file itu untuk melabel ulang.

## Status terakhir
Tahap 2 selesai: 102/102 lagu berlabel (`gemini-3.5-flash`, 6 request, ±170 detik). Hanya 1 lagu confidence < 0.6
(`Everything u Are` - Hindia, 0.40) yang perlu ditinjau manual. Test: 5 lulus (`tests/test_catalog.py`, `tests/test_labeling.py`).
Perhatian untuk Tahap 4-7: intent + rerank = 2 request per rekomendasi, sehingga 20 request/hari/model di Gemini free
tier tidak cukup untuk evaluasi; pertimbangkan Groq (1.000 request/hari, lebih cepat) untuk runtime.

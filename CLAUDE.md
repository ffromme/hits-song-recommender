# CLAUDE.md: hits-song-recommender

## Ringkasan proyek
Pemilik: Iam, mahasiswa Informatika yang sedang kerja praktek di HITS UNIKOM RADIO (media kampus).
Proyek besarnya adalah agent AI penyiar radio untuk live TikTok. Repo ini **hanya** memuat prototipe
**modul rekomendasi lagu**: komentar pendengar (eksplisit "putar lagu X" atau implisit berbasis mood/situasi)
diubah menjadi 1 lagu dari katalog, ditambah kalimat host.

Alur: komentar → `intent` (LLM) → `retrieval` (fuzzy match atau vector search + filter) → `rerank` (LLM pilih 1 + host_line) → `Recommendation`.
Cara setup, menjalankan, menambah lagu, dan evaluasi ada di `README.md`.

## Scope
- Di dalam scope: library Python `src/hits_rec/` + script CLI di `scripts/`.
- Di luar scope: TikTok, avatar 3D, TTS, dialog 2 agent, pemutar audio.
- Jangan mengunduh/memutar audio. Jangan menyalin atau menyimpan lirik berhak cipta.

## Aturan kerja
1. Kerjakan **per tahap**. Setelah tiap tahap: jalankan, tunjukkan output nyata, ringkas 3–5 kalimat, lalu **berhenti dan tunggu "lanjut"**.
2. Tanpa Jupyter notebook; hanya modul `.py` dan script terminal.
3. Jangan instal paket besar (mis. PyTorch GPU) tanpa memberi tahu dulu.
4. Keputusan desain yang punya beberapa opsi sama-masuk-akal: tanya singkat dulu. Kalau jelas: putuskan dan sebutkan alasannya.
5. Rahasia hanya di `.env` (di-ignore git). Template ada di `.env.example`. Sebelum commit, cek diff tidak berisi API key.
6. Komentar kode & README berbahasa Indonesia; nama variabel/fungsi berbahasa Inggris.
7. Jelaskan istilah teknis (embedding, vector DB, dsb.) dengan bahasa sederhana karena pemilik masih awam.
8. Jangan mengubah struktur direktori tanpa bertanya.

## Tahapan (semua selesai)
0. Scaffolding
1. Skema & katalog: `schemas.py`, `catalog.py` (ringkasan: `python -m hits_rec.catalog`)
2. Pelabelan mood: `llm.py`, `labeling.py`, `scripts/01_label_catalog.py`
3. Embedding & indeks: `embedding.py`, `index.py`, `scripts/02_build_index.py`
4. Intent: `intent.py` (demo: `python -m hits_rec.intent`)
5. Retrieval & filter: `retrieval.py` (demo: `python -m hits_rec.retrieval`)
6. Rerank & host_line: `rerank.py`, `pipeline.py` (demo: `python -m hits_rec.pipeline`)
7. CLI & evaluasi: `scripts/03_recommend.py`, `scripts/04_evaluate.py`, `data/eval/queries.yaml`
8. Rapikan: README, tests, file ini

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
├── outputs/                            # laporan evaluasi (eval_report.md)
└── tests/                              # test tanpa API: catalog, schemas, labeling, llm, intent, retrieval, rerank
```
`pyproject.toml` ditambahkan (disetujui) agar paket bisa diinstal editable (`pip install -e .`).
`.cache/` (di-ignore git): cache jawaban LLM (`.cache/llm/`) dan indeks ChromaDB (`.cache/chroma/`), aman dihapus.

## Keputusan teknis
- **Environment**: Windows 11, Python 3.14 (venv `.venv`), PyTorch **CPU** walau ada RTX 3050 6GB (model embedding
  kecil cukup cepat di CPU; versi GPU ±2,5 GB).
- **Windows Smart App Control** sempat memblokir DLL (`rpds`, `sklearn`). Pemilik mengubahnya ke mode Evaluation +
  restart. Jika muncul "An Application Control policy has blocked this file", cek log Code Integrity (event 3077).
  Jangan mengubah pengaturan keamanan Windows sendiri.
- **LLM**: provider gratis lewat API OpenAI-compatible (paket `openai`), dibungkus `llm.py`; diatur dari `.env`
  (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, opsional `LLM_REASONING_EFFORT`). Runtime: **Groq `qwen/qwen3.8-27b`**
  (±0,5 s/panggilan, 1.000 request/hari, **8.000 token/menit**). Pelabelan awal katalog memakai Gemini
  `gemini-3.5-flash` (gratis 20 request/hari PER MODEL; 3.7/3.8 sering 503) sehingga di-batch 20 lagu/request.
  OpenRouter `:free` dicoba tapi terlalu lambat (rata-rata 18 s) dan sering "provider overloaded".
- **Output LLM**: JSON diminta lewat prompt (bukan fitur provider) lalu divalidasi pydantic; JSON rusak dikirim
  balik ke LLM (maks 3x); respons HTTP 200 tanpa `choices` diulang 3x dengan jeda. Cache `.cache/llm/<sha256>.json`
  (kunci = model + reasoning_effort + prompt + schema); `llm.cache_enabled = False` untuk mengukur latensi.
- **Pelabelan**: hanya judul + artis + metadata CSV, tanpa lirik; confidence rendah bila tidak kenal lagunya.
  Inkremental: lagu yang sudah ada di `songs_labeled.jsonl` dilewati; hapus file itu untuk melabel ulang.
- **Embedding**: `intfloat/multilingual-e5-small` (bukan `paraphrase-multilingual-MiniLM-L12-v2`), karena dilatih
  khusus untuk pencarian kalimat pendek → dokumen. Wajib awalan `query: ` / `passage: `. Skor cosine mengumpul di
  0,80–0,88: pakai urutan, jangan ambang skor tetap.
- **Vector DB**: ChromaDB lokal (cosine, telemetry dimatikan), dibangun ulang penuh tiap `02_build_index.py`.
  Teks yang di-embed = mood_description + moods + suitable_situations (tanpa judul/artis).
- **Intent**: komentar dibungkus `<komentar>` sebagai string JSON dan diperlakukan sebagai data (anti prompt
  injection). explicit_song ikut mengisi mood_profile (untuk lagu mirip). Menyebut penyanyi = explicit_song.
  language_hint hanya bila diminta tegas, tidak ditebak dari bahasa komentar.
- **Retrieval**: fuzzy match `difflib` dengan `_match_key` (kata ulang "hati2" → "hati hati", spasi dibuang);
  judul DAN artis harus cocok bila keduanya diisi; artis kolaborasi ("feat.", "and", "&") dipecah. Mood: vector
  search k + len(cooldown), filter bahasa di ChromaDB (diabaikan bila bahasa itu tidak ada), cooldown, filter energi
  lunak (buang yang bertolak belakang, dahulukan yang sama). Konstanta di `config.py`.
- **Pipeline** (`Recommender.recommend`): moderasi/not_a_request → tanpa lagu. Eksplisit ditemukan → lagu itu (LLM
  hanya menulis host_line); hanya artis → LLM pilih dari lagu artis itu; tidak ada di katalog / kena cooldown →
  lagu mirip via mood_profile (tanpa filter bahasa). Mood kosong setelah filter → filter dilonggarkan. Rerank gagal /
  nomor di luar daftar → kandidat teratas + host_line bawaan. Lagu terpilih otomatis masuk riwayat (di memori).
  Model embedding dimuat di `Recommender.__init__` (startup ±10 s). Maks 8 kandidat ke LLM.
- **Evaluasi**: 22 query dijalankan berurutan dalam satu sesi; cek otomatis dari `expect`; cache LLM mati;
  `--pause 16` agar tidak kena batas token/menit Groq.

## Status terakhir
Semua tahap (0–8) selesai. Evaluasi terakhir (Groq `qwen/qwen3.8-27b`, cache OFF, jeda 16 s): cek otomatis 21/22
lolos; latensi total rata-rata 1,40 s, median 1,16 s, maks 3,98 s (intent median 0,65 s, retrieval 0,04 s, rerank
0,51 s). Test: 16 lulus (`pytest`, tanpa API).
Masalah terbuka:
- Mood samar ("hari ini capek tp seneng", "bosen bgt") kadang terbaca not_a_request; perlu keputusan pemilik apakah
  curhat tanpa minta lagu tetap dibalas lagu.
- host_line kadang kurang rapi (campur Inggris, "gue", typo); nilai manual di `outputs/eval_report.md` belum diisi.
- Lagu mirip untuk request eksplisit yang tidak ada di katalog kadang kurang nyambung (mis. Lathi → I'm Yours).
- Label beberapa lagu dipertanyakan (mis. "Menghapus Jejakmu" berlabel tinggi/positif); 1 lagu confidence rendah
  ("Everything u Are" - Hindia) belum dikoreksi manual.
- Batas Groq 8.000 token/menit (±3–4 rekomendasi/menit) membatasi live yang ramai.

## Ide lanjutan
- **Audio embedding** (mis. CLAP/MERT dari file audio milik radio) untuk melengkapi label mood berbasis pengetahuan
  LLM, terutama lagu yang kurang dikenal.
- **Integrasi ke antrian putar**: API/fungsi `enqueue(Recommendation)`, riwayat putar persisten (file/SQLite) agar
  cooldown bertahan antar-sesi, dan batas request per penonton.
- **Moderasi lebih ketat**: model/endpoint moderasi khusus sebelum LLM utama, daftar kata terlarang lokal, dan log
  komentar yang ditolak untuk ditinjau.
- **Hemat token/latensi**: kurangi RERANK_CANDIDATES / persingkat deskripsi kandidat, gabungkan intent + rerank
  dalam 1 panggilan untuk request mood, atau provider berbayar dengan batas token lebih besar.
- **Kualitas host_line**: contoh gaya penyiar HITS di prompt (few-shot), cek otomatis campur bahasa/panjang kalimat.
- **Lagu mirip yang lebih baik** untuk request di luar katalog: catat request yang tidak tersedia sebagai masukan
  penambahan katalog.
- **Evaluasi**: tambah query uji dari komentar live asli, ukur di bawah beban (banyak komentar per menit).

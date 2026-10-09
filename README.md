# hits-song-recommender

Prototipe **modul rekomendasi lagu** untuk agent penyiar AI HITS UNIKOM RADIO (live TikTok).
Modul ini menerima satu komentar penonton, baik yang **eksplisit** ("puterin hati2 dijalan tulus dong") maupun
**berbasis mood/situasi** ("lg excited nungguin kakak pulang dr rantau"), lalu memilih **satu lagu dari katalog**
dan menulis **kalimat pengantar ala penyiar** (`host_line`).

Di luar cakupan repo ini: integrasi TikTok, avatar 3D, TTS, dialog 2 agent, dan pemutar audio.
Modul ini tidak mengunduh/memutar audio dan tidak menyimpan lirik.

## Alur

```
komentar penonton
   │
   ▼
[1] intent (LLM) ──────── bukan request / perlu moderasi ──► tidak ada lagu
   │  explicit_song: judul/artis   mood_request: mood_profile + energi + bahasa
   ▼
[2] retrieval
   │  eksplisit: fuzzy match judul/artis di katalog (toleran typo)
   │     └ tidak ada di katalog / baru diputar ──► cari lagu mirip lewat mood
   │  mood: vector search 15 kandidat → filter bahasa, cooldown, energi
   ▼
[3] rerank (LLM): pilih 1 dari maks 8 kandidat + tulis alasan & host_line
   ▼
Recommendation(song, reason, host_line, candidates_considered)
```

Persiapan katalog (dijalankan sekali, dan diulang saat katalog berubah):

```
songs.csv ──[01_label_catalog: LLM]──► songs_labeled.jsonl ──[02_build_index: embedding]──► indeks ChromaDB
```

Hasil evaluasi terakhir (Groq `qwen/qwen3.8-27b`): 21/22 request uji lolos cek otomatis, latensi total median
1,16 s (maks 3,98 s). Detail di [outputs/eval_report.md](outputs/eval_report.md).

## Setup (Windows, PowerShell)

```powershell
# 1. Buat virtual environment (sekali saja). Python 3.10+; proyek ini memakai 3.14.
py -3.14 -m venv .venv

# 2. Aktifkan (setiap membuka terminal baru)
.\.venv\Scripts\Activate.ps1

# 3. Instal dependensi (±1,4 GB, termasuk PyTorch versi CPU) + paket proyek ini (mode editable)
pip install -r requirements.txt

# 4. Siapkan rahasia: salin template, lalu isi LLM_API_KEY
copy .env.example .env
```

Key gratis Groq bisa dibuat di https://console.groq.com/keys. Provider lain (Gemini, OpenRouter) ada sebagai
blok alternatif di `.env.example`; ganti provider cukup dengan mengubah 3 baris di `.env`, tanpa mengubah kode.

Saat pertama kali dijalankan, model embedding (`intfloat/multilingual-e5-small`, ±470 MB) diunduh otomatis.

> **Windows Smart App Control.** Jika muncul `ImportError: DLL load failed ... An Application Control policy has
> blocked this file`, Windows memblokir salah satu library. Di laptop pengembang, ini selesai setelah Smart App
> Control diubah ke mode *Evaluation* lalu laptop di-restart.

## Menjalankan

```powershell
python scripts/01_label_catalog.py    # labeli mood lagu yang belum berlabel (LLM)
python scripts/02_build_index.py      # bangun ulang indeks vektor + 3 query uji
python scripts/03_recommend.py        # CLI interaktif: ketik komentar, lihat lagu + host_line
python scripts/04_evaluate.py --pause 16   # evaluasi semua request uji -> outputs/eval_report.md
python scripts/05_web.py              # web UI sederhana di http://127.0.0.1:8000 (untuk demo/presentasi)
pytest                                # test (tanpa memanggil API)
```

Demo per modul: `python -m hits_rec.catalog` (ringkasan katalog), `python -m hits_rec.intent`,
`python -m hits_rec.retrieval`, `python -m hits_rec.pipeline`.

Contoh sesi CLI:

```
💬 komentar> nemenin nugas dong kak, ngantuk parah wkwk
   intent : mood_request | request mood
   lagu   : Lovely Day — Bill Withers  (dari 8 kandidat)
   alasan : Nada soul-nya yang hangat dan semangat positifnya cocok untuk mengusir ngantuk ...
   host   : Halo kalian yang lagi nugas sampai mata berat, ... 'Lovely Day' dari Bill Withers ...
   waktu  : intent=1.24s retrieval=1.22s rerank=0.51s total=2.97s
```

Memakai dari kode Python:

```python
from hits_rec.pipeline import Recommender

rec = Recommender()                       # muat katalog & model embedding sekali (±10 s)
result = rec.recommend("abis putus nih kak... puterin yg galau2")
if result.recommendation:
    print(result.recommendation.song.title, result.recommendation.host_line)
```

## Menambah atau mengubah lagu

1. Tambahkan baris di `data/raw/songs.csv`:

   | kolom | wajib | contoh | catatan |
   |---|---|---|---|
   | `title` | ya | Kangen | |
   | `artist` | ya | Dewa 19 | kolaborasi boleh ditulis "A feat. B" / "A and B" |
   | `language` | ya | `id` | kode ISO 639: `id`, `en`, `ko`, `jv`, ... |
   | `genre` | tidak | pop rock | |
   | `year` | tidak | 1992 | |

   CSV hasil Excel (pemisah `;`) juga bisa dibaca. Baris duplikat atau tidak valid dilewati dan dilaporkan
   (cek dengan `python -m hits_rec.catalog`).
2. `python scripts/01_label_catalog.py`: hanya lagu baru yang dikirim ke LLM (20 lagu per request).
   Tinjau daftar **confidence rendah** di akhir output: itu lagu yang kurang dikenali LLM.
3. `python scripts/02_build_index.py`: bangun ulang indeks.

Mengoreksi label secara manual: edit baris lagu di `data/labeled/songs_labeled.jsonl` (mis. `energy`, `moods`,
`mood_description`), lalu jalankan ulang `02_build_index.py`. Untuk melabeli ulang semua lagu, hapus file jsonl itu.

## Evaluasi

`data/eval/queries.yaml` berisi 22 request uji (eksplisit, hanya artis, tidak ada di katalog, cooldown, mood
jelas/samar, bahasa gaul/campuran, tidak relevan, tidak pantas, prompt injection). Tiap request punya `expect`
yang dicek otomatis, misalnya:

```yaml
- category: eksplisit
  comment: "kak puterin hati2 dijalan nya tulus dong 🥺🙏"
  expect: {type: explicit_song, song: "Hati-Hati di Jalan"}
```

Kunci `expect` yang tersedia: `type`, `song`, `artist`, `not_song`, `energy`, `language`, `moderation`, `no_song`
(penjelasan di bagian atas file yaml).

`python scripts/04_evaluate.py` menjalankan semuanya **berurutan dalam satu sesi** (cooldown ikut berlaku) dan
menulis `outputs/eval_report.md`: tabel request, intent, lagu, alasan, host_line, hasil cek otomatis, latensi per
langkah, dan kolom **nilai manual (1–5)** yang diisi sendiri. Di bagian atas ada ringkasan latensi.

- Cache LLM **mati** secara default agar latensi yang terukur nyata. `--cache` menyalakannya (gratis & cepat untuk
  run ulang, tapi latensinya jadi tidak realistis).
- `--pause 16` memberi jeda antar-request agar tidak kena batas 8.000 token/menit Groq.

## Konfigurasi

`.env`: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, dan opsional `LLM_REASONING_EFFORT` (`low` = lebih cepat).

`src/hits_rec/config.py`:

| konstanta | nilai | arti |
|---|---|---|
| `COOLDOWN_N` | 10 | lagu yang diputar dalam 10 lagu terakhir tidak direkomendasikan lagi |
| `TOP_K_CANDIDATES` | 15 | kandidat dari vector search untuk request mood |
| `RERANK_CANDIDATES` | 8 | kandidat yang dikirim ke LLM untuk dipilih |
| `FUZZY_MIN_SCORE` | 0.8 | kemiripan minimal judul/artis untuk request eksplisit |
| `LOW_CONFIDENCE` | 0.6 | batas confidence label yang perlu ditinjau manual |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | model embedding multibahasa |

Cache lokal ada di `.cache/` (jawaban LLM dan indeks ChromaDB). Aman dihapus; akan dibuat ulang.

## Struktur folder

```
data/raw/songs.csv                 katalog mentah
data/labeled/songs_labeled.jsonl   label mood dari LLM (1 lagu per baris)
data/eval/queries.yaml             request uji + ekspektasi
src/hits_rec/
  config.py      .env, path, konstanta          schemas.py    model data (pydantic)
  catalog.py     baca & validasi songs.csv       llm.py        pemanggilan LLM + cache + retry
  labeling.py    pelabelan mood (batch)          embedding.py  teks -> embedding
  index.py       simpan/cari di ChromaDB         intent.py     komentar -> Intent
  retrieval.py   fuzzy match, vector search, filter, riwayat putar
  rerank.py      LLM pilih 1 lagu + host_line    pipeline.py   menyatukan semuanya (Recommender)
scripts/         01_label_catalog, 02_build_index, 03_recommend, 04_evaluate
outputs/         laporan evaluasi
tests/           test kecil (tanpa API)
```

## Batasan yang perlu diketahui

- **Batas provider gratis.** Groq: 8.000 token/menit (1 rekomendasi ±2.200 token, jadi ±3–4 rekomendasi/menit) dan
  1.000 request/hari. Gemini gratis: 20 request/hari per model, dan datanya dipakai Google untuk melatih model.
- **Riwayat putar hanya di memori**: hilang saat program ditutup.
- **Label mood berasal dari pengetahuan LLM** tentang judul + artis, bukan dari audio. Lagu yang kurang dikenal
  mendapat confidence rendah dan perlu dicek manual.
- **host_line kadang kurang rapi** (campur bahasa Inggris, typo). Nilai manual di laporan evaluasi membantu
  memantau ini.

## Glosarium

- **LLM**: model bahasa besar (mis. Qwen, Gemini) yang dipakai untuk memahami komentar, melabeli lagu, dan menulis
  kalimat host.
- **Embedding**: deretan angka (di sini 384 angka) yang mewakili makna teks. Teks yang maknanya mirip menghasilkan
  angka yang berdekatan, walau kata-katanya berbeda.
- **Vector DB (ChromaDB)**: tempat menyimpan embedding semua lagu dan mencari yang paling dekat dengan embedding
  komentar. Berjalan lokal sebagai file, tanpa server.
- **Cosine similarity**: ukuran kemiripan dua embedding (0–1). Untuk model ini skornya cenderung mengumpul di
  0,80–0,88, jadi yang penting urutannya.
- **Fuzzy match**: pencocokan teks yang toleran typo ("Separuh Napas" ≈ "Separuh Nafas").
- **Intent**: maksud komentar: minta lagu tertentu, minta lagu sesuai mood, atau bukan permintaan lagu.
- **Rerank**: memilih ulang 1 lagu terbaik dari beberapa kandidat hasil pencarian.
- **Cooldown**: lagu yang baru diputar tidak direkomendasikan lagi untuk sementara.
- **Prompt injection**: komentar yang berusaha menyuruh LLM melanggar aturannya. Komentar selalu diperlakukan
  sebagai data, bukan perintah.

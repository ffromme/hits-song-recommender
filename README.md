# hits-song-recommender

Prototipe modul rekomendasi lagu untuk agent penyiar HITS UNIKOM RADIO. Modul ini menerima komentar
pendengar, baik yang eksplisit ("putar Kangen dari Dewa 19") maupun berbasis mood ("lagi excited nunggu kakak pulang"),
lalu memilih satu lagu dari katalog dan menulis kalimat pengantar ala penyiar.

> Status: **Tahap 0 (scaffolding)**. README ini akan dilengkapi di Tahap 8.

## Setup (Windows, PowerShell)

```powershell
# 1. Buat virtual environment (sekali saja)
py -3.14 -m venv .venv

# 2. Aktifkan
.\.venv\Scripts\Activate.ps1

# 3. Instal dependensi (termasuk paket proyek ini dalam mode editable)
pip install -r requirements.txt

# 4. Siapkan rahasia
copy .env.example .env
# lalu isi LLM_API_KEY di file .env (default: key Gemini gratis dari https://aistudio.google.com/apikey)
```

## Katalog lagu

Isi katalog ada di `data/raw/songs.csv` dengan kolom:

| kolom | wajib | contoh |
|---|---|---|
| `title` | ya | Kangen |
| `artist` | ya | Dewa 19 |
| `language` | ya | `id` / `en` |
| `genre` | tidak | pop rock |
| `year` | tidak | 1992 |

File saat ini hanya berisi 10 contoh baris sebagai template. Ganti dengan katalog asli.

## Script

Akan ditambahkan per tahap:

- `scripts/01_label_catalog.py`: pelabelan mood lagu oleh LLM
- `scripts/02_build_index.py`: membangun indeks vektor
- `scripts/03_recommend.py`: CLI interaktif
- `scripts/04_evaluate.py`: evaluasi dengan kumpulan request uji

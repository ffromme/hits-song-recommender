"""Tahap 7: CLI interaktif. Ketik komentar seperti penonton live, lihat lagu yang dipilih + kalimat host.

Riwayat putar (cooldown) berlaku selama sesi berjalan, seperti saat live.
Pemakaian:  python scripts/03_recommend.py      (ketik "keluar" atau tekan Enter kosong untuk berhenti)
"""
import time

from hits_rec.config import COOLDOWN_N, LLM_MODEL
from hits_rec.pipeline import Recommender, format_result


def main() -> None:
    print(f"Memuat katalog & model embedding ... (LLM: {LLM_MODEL})")
    start = time.perf_counter()
    recommender = Recommender()
    print(f"Siap dalam {time.perf_counter() - start:.1f} s. Cooldown: {COOLDOWN_N} lagu terakhir.\n")

    while True:
        try:
            comment = input("💬 komentar> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if comment.lower() in ("", "keluar", "exit", "quit"):
            break
        print(format_result(recommender.recommend(comment)), "\n")
    print("Sampai jumpa!")


if __name__ == "__main__":
    main()

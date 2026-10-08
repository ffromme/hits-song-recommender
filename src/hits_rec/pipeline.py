"""Pipeline lengkap: komentar penonton -> Recommendation.

    komentar -> intent (LLM) -> retrieval (fuzzy / vector + filter) -> rerank (LLM) -> Recommendation

Pemakaian:
    rec = Recommender()                  # memuat katalog & model embedding sekali (beberapa detik)
    result = rec.recommend("lagi galau nih kak")
    result.recommendation                # None bila tidak ada lagu (bukan request / moderasi / tidak ada kandidat)

Setiap lagu yang direkomendasikan otomatis masuk riwayat putar (cooldown).
Jalankan `python -m hits_rec.pipeline` untuk demo.
"""
import time

from hits_rec.config import RERANK_CANDIDATES
from hits_rec.embedding import embed_query
from hits_rec.intent import parse_intent
from hits_rec.rerank import rerank
from hits_rec.retrieval import PlayHistory, catalog, find_explicit, search_by_mood
from hits_rec.schemas import Intent, LabeledSong, PipelineResult


def _songs(scored: list[tuple[LabeledSong, float]]) -> list[LabeledSong]:
    return [song for song, _ in scored]


class Recommender:
    def __init__(self, history: PlayHistory | None = None):
        self.history = history or PlayHistory()
        catalog()
        embed_query("pemanasan")  # muat model embedding sekarang, bukan saat komentar pertama masuk

    def recommend(self, comment: str) -> PipelineResult:
        timings: dict[str, float] = {}
        start = time.perf_counter()

        def finish(note: str, intent: Intent | None = None, recommendation=None) -> PipelineResult:
            timings["total"] = time.perf_counter() - start
            return PipelineResult(comment=comment, intent=intent, recommendation=recommendation,
                                  note=note, timings=timings)

        step = time.perf_counter()
        try:
            intent = parse_intent(comment)
        except Exception as err:
            return finish(f"intent gagal: {err}")
        timings["intent"] = time.perf_counter() - step

        if intent.needs_moderation:
            return finish("komentar perlu moderasi, tidak direspons dengan lagu", intent)
        if intent.type == "not_a_request":
            return finish("bukan permintaan lagu", intent)

        step = time.perf_counter()
        candidates, situation, note = self._retrieve(intent, comment)
        timings["retrieval"] = time.perf_counter() - step
        if not candidates:
            return finish(note, intent)

        step = time.perf_counter()
        recommendation = rerank(comment, situation, candidates[:RERANK_CANDIDATES])
        timings["rerank"] = time.perf_counter() - step

        self.history.add(recommendation.song.song_id)
        return finish(note, intent, recommendation)

    def _retrieve(self, intent: Intent, comment: str) -> tuple[list[LabeledSong], str, str]:
        """Kembalikan (kandidat, situasi untuk LLM, catatan jalur)."""
        if intent.type == "explicit_song":
            requested = " - ".join(x for x in (intent.title, intent.artist) if x)
            matches = [song for song, _ in find_explicit(intent.title, intent.artist)]
            fresh = [s for s in matches if s.song_id not in self.history]
            if fresh and intent.title:
                return fresh[:1], "Penonton meminta lagu ini secara langsung. Tulis host_line pengantarnya.", \
                    "request eksplisit ditemukan di katalog"
            if fresh:
                return fresh, f"Penonton minta lagu dari {intent.artist}. Pilih yang paling cocok dengan suasana komentar.", \
                    "request artis ditemukan, LLM memilih lagunya"
            if matches:
                situation = (f"Lagu yang diminta ({requested}) baru saja diputar. Pilih alternatif yang mirip dan "
                             f"sampaikan dengan ramah bahwa lagu itu barusan sudah diputar.")
                note = "lagu yang diminta baru diputar (cooldown), disarankan yang mirip"
            else:
                situation = (f"Lagu yang diminta ({requested}) belum ada di katalog radio. Pilih alternatif yang "
                             f"paling mirip dan sampaikan dengan sopan bahwa lagu aslinya belum tersedia.")
                note = "lagu tidak ada di katalog, disarankan yang mirip"
            if not intent.mood_profile:
                return [], "", f"{note}: gagal, LLM tidak tahu mood lagu yang diminta"
            # Lagu mirip: pakai mood lagu yang diminta, tanpa filter bahasa (bahasa lagu aslinya belum tentu cocok)
            return _songs(search_by_mood(intent.mood_profile, intent.energy_hint, None, self.history)), situation, note

        # mood_request
        profile = intent.mood_profile or comment
        situation = "Penonton minta lagu sesuai perasaan/situasinya. Pilih yang paling cocok."
        candidates = _songs(search_by_mood(profile, intent.energy_hint, intent.language_hint, self.history))
        if candidates:
            return candidates, situation, "request mood"
        # Semua kandidat tersaring: longgarkan filter energi & bahasa (cooldown tetap berlaku)
        candidates = _songs(search_by_mood(profile, history=self.history))
        return candidates, situation, "request mood (filter dilonggarkan)" if candidates else "tidak ada kandidat"


DEMO_COMMENTS = [
    "kak puterin hati2 dijalan nya tulus dong 🥺🙏",
    "req lathi weird genius dong kak 🔥",
    "puterin lagu ed sheeran dong, lagi kasmaran nih hehe",
    "lg excited bgt nungguin kakak pulang dr rantau, lagu apa ya yg cocok?? 😆",
    "abis putus nih kak... sedih bgt 😭 puterin yg galau2",
    "kak puterin hati hati di jalan lagi dong, td telat masuk live",
    "halo kak salam dari bandung 👋",
    "lagu buat orang2 b*doh kayak si admin, dasar t*l*l",
]


if __name__ == "__main__":
    from hits_rec.config import LLM_MODEL

    start = time.perf_counter()
    recommender = Recommender()
    print(f"Model LLM: {LLM_MODEL} | startup: {time.perf_counter() - start:.1f} s\n")
    for comment in DEMO_COMMENTS:
        result = recommender.recommend(comment)
        t = result.timings
        steps = " ".join(f"{k}={v:.2f}s" for k, v in t.items())
        print(f"💬 {comment}")
        print(f"   intent : {result.intent.type if result.intent else '-'} | {result.note}")
        if result.recommendation:
            r = result.recommendation
            print(f"   lagu   : {r.song.title} — {r.song.artist}  (dari {len(r.candidates_considered)} kandidat)")
            print(f"   alasan : {r.reason}")
            print(f"   host   : {r.host_line}")
        print(f"   waktu  : {steps}\n")

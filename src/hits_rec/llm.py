"""Pembungkus pemanggilan LLM.

- Provider apa pun yang punya API "OpenAI-compatible" (Gemini, Groq, OpenRouter, ...) bisa dipakai;
  cukup ganti LLM_API_KEY / LLM_BASE_URL / LLM_MODEL di .env.
- Jawaban diminta berupa JSON, lalu diperiksa dengan model pydantic. Kalau JSON rusak atau tidak sesuai,
  pesan error-nya dikirim balik ke LLM untuk diperbaiki (maksimal `max_attempts` kali).
- Jawaban yang valid disimpan ke disk (.cache/llm/). Panggilan yang persis sama berikutnya diambil dari
  cache, jadi tidak memakan kuota/biaya lagi.
"""
import hashlib
import json
import re
import time
from collections import Counter
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from hits_rec.config import LLM_API_KEY, LLM_BASE_URL, LLM_CACHE_DIR, LLM_MODEL, LLM_REASONING_EFFORT

T = TypeVar("T", bound=BaseModel)

# Hitungan sederhana untuk dilaporkan script: berapa panggilan API vs diambil dari cache
stats: Counter = Counter()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY belum diisi di .env (lihat .env.example).")
        # max_retries: SDK otomatis menunggu & mengulang saat kena rate limit (429) atau error server
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, max_retries=5, timeout=120)
    return _client


def _extract_json(text: str) -> str:
    """Ambil isi JSON dari jawaban LLM, membuang pembungkus ```json ... ``` bila ada."""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def _chat(messages: list[dict], max_empty: int = 3) -> str:
    """Satu panggilan chat. Error HTTP (429/5xx) sudah diulang otomatis oleh SDK.

    Beberapa provider (mis. OpenRouter) mengirim error di dalam respons HTTP 200 tanpa jawaban,
    mis. "provider overloaded". Respons kosong seperti itu diulang dengan jeda 2, 4, ... detik.
    """
    extra = {"reasoning_effort": LLM_REASONING_EFFORT} if LLM_REASONING_EFFORT else {}
    for attempt in range(1, max_empty + 1):
        stats["api_calls"] += 1
        response = _get_client().chat.completions.create(model=LLM_MODEL, messages=messages, **extra)
        if response.choices:
            return response.choices[0].message.content or ""
        error = (response.model_extra or {}).get("error", "respons kosong")
        if attempt == max_empty:
            raise RuntimeError(f"LLM tidak memberi jawaban setelah {max_empty} percobaan: {error}")
        stats["empty_retries"] += 1
        time.sleep(2 * attempt)
    raise AssertionError("unreachable")


def complete_json(system: str, user: str, schema: type[T], max_attempts: int = 3) -> T:
    """Kirim prompt ke LLM dan kembalikan jawaban yang sudah tervalidasi sebagai objek `schema`."""
    key_src = json.dumps([LLM_MODEL, LLM_REASONING_EFFORT, schema.__name__, system, user], ensure_ascii=False)
    cache_path = LLM_CACHE_DIR / f"{hashlib.sha256(key_src.encode()).hexdigest()}.json"
    if cache_path.exists():
        stats["cache_hits"] += 1
        return schema.model_validate_json(cache_path.read_text(encoding="utf-8"))

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for attempt in range(1, max_attempts + 1):
        text = _chat(messages)
        try:
            result = schema.model_validate_json(_extract_json(text))
        except ValidationError as err:
            if attempt == max_attempts:
                raise RuntimeError(f"JSON dari LLM tetap tidak valid setelah {max_attempts} percobaan: {err}") from err
            stats["retries"] += 1
            # Kirim balik jawaban + error-nya supaya LLM memperbaiki
            messages += [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"JSON tidak valid:\n{err}\nKirim ulang HANYA JSON yang sudah diperbaiki."},
            ]
            continue
        LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(result.model_dump_json(), encoding="utf-8")
        return result
    raise AssertionError("unreachable")

"""Test llm.py tanpa memanggil API: klien LLM dipalsukan."""
from types import SimpleNamespace

from pydantic import BaseModel

from hits_rec import llm


class Answer(BaseModel):
    ok: bool


def fake_client(responses):
    """Klien palsu yang mengembalikan respons dari daftar secara berurutan."""
    queue = iter(responses)
    create = lambda **kwargs: next(queue)  # noqa: E731
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))], model_extra={})


EMPTY = SimpleNamespace(choices=None, model_extra={"error": {"message": "provider overloaded"}})


def test_complete_json_retries_empty_response_and_bad_json(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "LLM_CACHE_DIR", tmp_path)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    # respons kosong -> JSON rusak -> JSON benar dalam blok ```json
    monkeypatch.setattr(llm, "_client", fake_client([EMPTY, reply("bukan json"), reply('```json\n{"ok": true}\n```')]))
    assert llm.complete_json("sys", "user", Answer) == Answer(ok=True)
    # panggilan kedua yang sama diambil dari cache (klien palsu sudah habis, jadi akan error bila dipanggil)
    assert llm.complete_json("sys", "user", Answer) == Answer(ok=True)

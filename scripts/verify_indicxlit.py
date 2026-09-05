"""Verification script for the ai4bharat-transliteration (IndicXlit) engine.

Run with the Python 3.10 venv:  .venv310\\Scripts\\python.exe scripts\\verify_indicxlit.py

Checks the installed API, smoke-tests 9 Hinglish words for Hindi, and measures
single-call + batch latency on CPU.
"""
import sys, io, time, inspect, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from ai4bharat.transliteration import XlitEngine

TEST_WORDS = ["bahut", "bht", "bohot", "kaha", "uske", "padega", "chalega", "nahi", "karna"]

print("=== API CONFIRMATION ===")
print("XlitEngine:", XlitEngine)
print("XlitEngine is a factory function:", not isinstance(XlitEngine, type))
print("Signature:", inspect.signature(XlitEngine))

print("\n=== INIT (lang2use='hi', beam_width=4, rescore=True) ===")
engine = XlitEngine(lang2use="hi", beam_width=4, rescore=True)
print("engine type:", type(engine).__name__)
print("tgt_langs:", engine.tgt_langs)

print("\n=== SMOKE TEST: 9 words (top-4 candidates, ordered by rank) ===")
for w in TEST_WORDS:
    out = engine.translit_word(w, lang_code="hi", topk=4)
    print(f"{w!r:10} -> {json.dumps(out, ensure_ascii=False)}")

print("\n=== LATENCY: single call (bahut), warm-up then 10 timed runs ===")
engine.translit_word("bahut", lang_code="hi", topk=4)
times = []
for _ in range(10):
    t0 = time.perf_counter()
    engine.translit_word("bahut", lang_code="hi", topk=4)
    times.append((time.perf_counter() - t0) * 1000.0)
print(f"single-call mean: {sum(times) / len(times):.2f} ms   max: {max(times):.2f} ms")

print("\n=== BATCH API ===")
print("has batch_transliterate_words:", hasattr(engine, "batch_transliterate_words"))
print("signature:", inspect.signature(engine.batch_transliterate_words))

print("\n=== LATENCY: batch of 50 words ===")
batch50 = (TEST_WORDS * 6)[:50]
engine.batch_transliterate_words(batch50[:5], "en", "hi", topk=4)
t0 = time.perf_counter()
res = engine.batch_transliterate_words(batch50, "en", "hi", topk=4)
total_ms = (time.perf_counter() - t0) * 1000.0
print(f"batch-50 total: {total_ms:.2f} ms   per-word avg: {total_ms / 50:.2f} ms")
print(f"n results: {len(res)}  len(res[0]): {len(res[0]) if res else None}  (repeated inputs collapse)")
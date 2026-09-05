# IndicXlit Verification Report

**Date:** 2026-09-05 · **Scope:** verify `ai4bharat-transliteration` (IndicXlit) for
future Hinglish vocabulary normalization — testing only, no `canonical_map.json` built.

## Environment

| Item | Value |
|---|---|
| Python | 3.10.11 (new venv `.venv310` — 3.13 couldn't build fairseq) |
| Packages | `ai4bharat-transliteration` 1.1.3, fairseq 0.12.2 (patched), torch 2.14.0 CPU |
| GPU | RTX 4050 present but **unused** (CPU-only build by design) |
| Models | auto-downloaded on first init (~933 MB total: 121 MB model + 812 MB word-prob dicts) |

Two fixes were applied to the installed fairseq because no C++ toolchain exists on this machine:
1. `checkpoint_utils.py` — `torch.load(..., weights_only=False)` (2 sites). PyTorch ≥2.6 rejects the checkpoint's `argparse.Namespace` pickle otherwise.
2. `fairseq/data/data_utils_fast.py` — pure-Python shim (transcribed from the `.pyx`) for `batch_by_size_fn` / `batch_by_size_vec` / `batch_fixed_shapes_fast`; the Cython module can't be compiled here.

## Smoke test — 9 Hinglish words → Hindi (top-4 candidates)

| Word | Candidates (rank order) | Top-1 correct? |
|---|---|---|
| bahut | बहुत, बहूत, बहत, बहुट | ✅ |
| bht | भट, भट्, बहत, भत | ❌ (top = भट, not बहुत) |
| bohot | बोहोत, बोहोट, बहोत, बोहट | ⚠️ top is बोहोत; बहोत is rank 3 |
| kaha | कहा, कह, कह्, काह | ✅ |
| uske | उसके, उस्के, ऊसके, उसकें | ✅ |
| padega | पड़ेगा, पडेगा, पदेगा, पड़ेगे | ✅ |
| chalega | चलेगा, चालेगा, छलेगा, चलेग | ✅ |
| nahi | नही, नाही, नहि, नाहि | ⚠️ nukta dropped (नहीं) |
| karna | करना, कारना, कर्णा, कर्ण | ✅ |

No numeric confidence scores are exposed — only ranked candidate strings.

## Latency (CPU)

| Scenario | Total | Per word |
|---|---|---|
| Single call, warm-up + 10 runs | mean **51–56 ms**, max **56–59 ms** | — |
| Batch of 50 (one call) | **~347–354 ms** | **~7 ms/word** (~8× faster) |

Native batch API exists: `batch_transliterate_words(words, src_lang, tgt_lang, topk)`.
⚠️ Caveat: identical repeated inputs collapse in `post_process` (50 inputs with 9
unique words → 36 candidates). Always pass distinct words per batch call.

## Verdict

IndicXlit is usable on CPU for our use case. Prefer **batched** transliteration.
Watch out for `bht` → भट and `nahi` → नही (missing nukta); a `canonical_map.json`
build step should account for abbreviations and manual nukta corrections.

**Reproduce:** `.venv310\Scripts\python.exe scripts\verify_indicxlit.py`
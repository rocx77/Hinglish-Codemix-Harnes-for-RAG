# TODO — IndicXlit Verification Task

> Testing only. Do NOT build canonical_map.json or process the full PHINC
> vocabulary yet. Stop after producing the Step 4 summary.

## Step 1 — Environment check
- [x] Confirm active Python is 3.10.x (`python --version`)
- [x] Confirm PyTorch installed with CUDA (expect RTX 4050)
- [x] Confirm / install `ai4bharat-transliteration` (`pip show`); capture traceback on failure

## Step 2 — Load model and smoke-test
- [x] Confirm the correct import path / API from the installed package
- [x] Initialize engine for Hindi (`lang='hi'` or equivalent)
- [x] Transliterate the 9 test words (`bahut bht bohot kaha uske padega chalega nahi karna`), print full output structure incl. candidates/confidence

## Step 3 — Measure latency
- [x] Time single call for `bahut` (warm-up + 10 runs) → mean & max ms
- [x] Check if batch/list input API exists (inspect signature/docstring)
- [x] If batch: time 50-word batch → total + per-word ms
- [ ] If not: time 50 sequential single calls → total + per-word ms, note "not batched"

## Step 4 — Structured summary
- [x] Print summary table: Python version, CUDA/GPU, package status, 9 words, single-call latency, batch/sequential latency, full errors/warnings

---

## Results (2026-09-05)

| Item | Value |
|---|---|
| Python | 3.10.11 (`.venv310\Scripts\python.exe`) |
| PyTorch | 2.14.0 **+cpu** (CUDA build NOT installed — per decision), `torch.cuda.is_available() = False` |
| GPU hardware | RTX 4050 present but unused by this setup |
| ai4bharat-transliteration | **1.1.3** (fairseq 0.12.2 locally patched) |
| API | `XlitEngine(lang2use="hi", beam_width=4, rescore=True)` → `XlitEngineTransformer_En2Indic`, `tgt_langs={'hi'}` |

**9 words (top-4 candidates, no numeric confidence exposed — only rank order):**

| Word | Candidates (OrderedDict order = rank) |
|---|---|
| bahut | बहुत, बहूत, बहत, बहुट |
| bht | भट, भट्, बहत, भत  ⚠ top ≠ बहुत |
| bohot | बोहोत, बोहोट, बहोत, बोहट |
| kaha | कहा, कह, कह्, काह |
| uske | उसके, उस्के, ऊसके, उसकें |
| padega | पड़ेगा, पडेगा, पदेगा, पड़ेगे |
| chalega | चलेगा, चालेगा, छलेगा, चलेग |
| nahi | नही, नाही, नहि, नाहि  ⚠ top lacks nukta (नहीं) |
| karna | करना, कारना, कर्णा, कर्ण |

**Latency (CPU):**

| Scenario | Total | Per word |
|---|---|---|
| Single call (`bahut`), warm-up + 10 runs | mean **55.94 ms**, max **59.16 ms** | — |
| Batch of 50 (`batch_transliterate_words`, one call) | **353.73 ms** | **7.07 ms** (~8× faster/word) |

**Native batch API:** yes — `batch_transliterate_words(words: list, src_lang, tgt_lang, topk)` (internal, on `XlitEngineTransformer_En2Indic`). Caveat: in the 50-word test (9 unique × repeats) it returned **36** candidates, i.e. identical repeated inputs collapse in `post_process` — the library itself flags this (`FIXME` in `base_engine.py:batch_transliterate_words`). Feed distinct words per batch call.

**Errors/warnings hit & fixed:**
1. PyTorch ≥2.6 `torch.load(weights_only=True)` default → checkpoint pickle (`argparse.Namespace`) rejected. Fixed: `fairseq/checkpoint_utils.py` `weights_only=False` (2 sites).
2. `fairseq.data.data_utils_fast` (Cython) missing — no MSVC toolchain on machine. Fixed: wrote pure-Python shim `fairseq/data/data_utils_fast.py` (transcribed from sdist `.pyx`) with `batch_by_size_fn` / `batch_by_size_vec` / `batch_fixed_shapes_fast`.
3. Benign warnings only: `torch.jit.script` deprecated (FutureWarning), `pin_memory` no accelerator (UserWarning ×2), fairseq tensorboardX INFO.
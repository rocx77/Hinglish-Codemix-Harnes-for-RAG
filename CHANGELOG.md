# CHANGELOG

## [2026-09-04] Project restructure and PHINC cleaning (Steps 1-4)

### Structure changes

- Created `scripts/` directory for pipeline scripts (numbered order).
- Moved `Datasets/clean_phinc.py` -> `scripts/clean_phinc.py`; updated paths
  to use `ROOT` relative resolution so scripts run from project root.
- Deleted `Datasets/clean_phinc.py` (old location).
- Added `ftfy` and `rapidfuzz` to `requirements.txt`.
- Created `AGENTS.md` with project conventions, pipeline status, and next steps.

### PHINC cleaning results (Steps 1-4)

| Metric | Count |
|---|---|
| Total rows (raw) | 13,738 |
| Dropped (null/empty) | 0 |
| Remaining after Step 1 | 13,738 |
| Dropped (exact-dup on English_Translation_clean) | 282 |
| Remaining after Step 4 exact-dedup | 13,456 |
| translation_too_short = True (< 4 words) | 849 |
| Near-duplicate groups (size > 1) | 22 |

**Output:** `Datasets/phinc_cleaned_step1to4.csv`

Columns: `Sentence`, `Sentence_clean`, `English_Translation`,
`English_Translation_clean`, `translation_too_short`, `near_dup_group_id`

**Near-dup detail:** 22 groups, mostly pairs (size 2), one group of 3.
Flagged but not dropped — left for manual review in Step 5.

## [2026-09-04] Fix mention-handling in clean_phinc.py

Changed `RE_MENTION` from `@\w+` (delete entire mention) to `@(\w+)` with
replacement `\1` (strip only the `@`, keep the word). Same treatment as
hashtags. Applied to both `Sentence_clean` and `English_Translation_clean`.

Regenerated `phinc_cleaned_step1to4.csv`. Updated counts:

| Metric | Before | After |
|---|---|---|
| Dropped (exact-dup) | 282 | 227 |
| Remaining after Step 4 | 13,456 | 13,511 |
| translation_too_short | 849 | 532 |
| Near-dup groups (size > 1) | 22 | 5 |

Fewer short translations because previously `@someUSER` lost the word,
leaving emptier sentences. Near-dup count dropped because preserved words
make translations more distinct.

## [2026-09-05] Broaden URL detection in clean_phinc.py (Steps 2 & 3)

Replaced `RE_URL` (was `https?://\S+|www\.\S+`) with a pattern that also
matches bare short-link domains with **no protocol prefix and no preceding
whitespace** (e.g. `bhaiyapic.twitter.com/FvLEv3onxZ`):

- `(?:pic\.)?twitter\.com/\S+` — twitter.com and pic.twitter.com
- `t\.co/\S+`, `bit\.ly/\S+` — short links
- plus the existing `https?://\S+` and `www\.\S+`

Applied in the shared `clean_text()` used by both `Sentence_clean` and
`English_Translation_clean`; matches are replaced with `""` and the existing
`RE_MULTI_WS` normalization collapses any resulting double spaces. Garbled
mistranslated URL remnants (e.g. `Favlave 3xx`, `Http: //twitter.com/...`)
are intentionally left as-is for manual review.

Verified: of 1,344 raw `Sentence` rows containing bare-domain links, 0 retain
the domain after cleaning. Regenerated `phinc_cleaned_step1to4.csv`.

| Metric | Before (9/4) | After |
|---|---|---|
| Dropped (exact-dup) | 227 | 228 |
| Remaining after Step 4 | 13,511 | 13,510 |
| translation_too_short (pre-dedup) | 532 | 534 |
| Near-dup groups (size > 1) | 5 | 5 |

The 1-row deltas in exact-dup / too-short / remaining are a direct effect of
removing extra URL text (shifts the word counts that feed both metrics); the
near-dup structure is unchanged.

## [2026-09-05] IndicXlit verification — Python 3.10 env + smoke/latency test

### Environment setup

- Installed Python 3.10.11 (system was on 3.13/3.14 — fairseq 0.12.2 cannot
  build there).
- Created `.venv310` (from Python 3.10.11). Installed patched **fairseq 0.12.2**
  (sdist patched in `setup.py` to `extensions = []`, since the MSVC toolchain
  is absent on this machine) and **ai4bharat-transliteration 1.1.3** + torch
  2.14.0 CPU-only (CUDA build intentionally NOT installed — verification is
  CPU per user decision; RTX 4050 exists but unused).
- After install, two runtime fixes were needed in the installed fairseq:
  - `fairseq/checkpoint_utils.py`: `torch.load(..., weights_only=False)` at 2
    sites — torch ≥2.6 defaulted `weights_only=True`, which rejects the
    checkpoint's `argparse.Namespace` pickle.
  - Wrote pure-Python `fairseq/data/data_utils_fast.py` (transcribed 1:1 from
    the `.pyx` in the sdist) — `batch_by_size_fn` / `batch_by_size_vec` /
    `batch_fixed_shapes_fast` — since the Cython build needs a C++ toolchain.
- Models auto-downloaded to
  `.venv310\Lib\site-packages\ai4bharat\transliteration\transformer\models\en2indic\v1.0\`
  (model 121 MB, word-prob dicts 812 MB).

### Verification results (CPU, engine = `XlitEngine(lang2use="hi", beam_width=4)`)

9 test words top-1: bahut→बहुत ✓, bht→**भट** ⚠, bohot→बोहोत, kaha→कहा ✓,
uske→उसके ✓, padega→पड़ेगा ✓, chalega→चलेगा ✓, nahi→**नही** ⚠ (nukta drop),
karna→करना ✓.

Latency: single-call mean 55.94 ms / max 59.16 ms (warm-up + 10 runs);
50-word native batch call 353.73 ms total → **7.07 ms/word** (~8× faster than
sequential single calls). Native batch API confirmed:
`batch_transliterate_words(words, src_lang, tgt_lang, topk)` — caveat: repeated
identical inputs collapse in `post_process` (36 outputs for 50 inputs with
9 unique words); pass distinct words per call.

Summary table written to `todo.md`. Verification only — no `canonical_map.json`
built, no PHINC vocabulary processed.

### Follow-ups

- Added `scripts/verify_indicxlit.py` — reusable verification script (API check,
  9-word smoke test, single-call + batch latency). Run with `.venv310`.
- Added `indicxlit_verification_report.md` — short report with env, fixes,
  smoke-test table, latency, and batch API caveats.

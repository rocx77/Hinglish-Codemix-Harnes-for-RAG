# CHANGELOG

## [2026-09-11] P1 rules-layer pre-filter built, validated, and run on full vocab

- Created `scripts/wordnet_hinglish_filter.py` — offline, zero-cost deterministic
  pre-filter for the P1 collision problem. Five labels: NON_LINGUISTIC / AMBIGUOUS /
  HINGLISH / ENGLISH / UNCERTAIN_NEEDS_LLM.
- Created `scripts/export_phinc_vocab.py` — one-shot export of the full PHINC
  vocabulary with per-token row-occurrence frequencies (`reports/vocab_phinc_freq.tsv`).
- Full-vocab run on 29,579 unique tokens (165,692 row-occurrences):
  - Resolved for free: 14,801 tokens (50.0%) — 8,573 NON_LINGUISTIC, 4 AMBIGUOUS,
    49 HINGLISH, 6,176 ENGLISH (5,986 exact + 190 guarded-fuzzy).
  - UNCERTAIN_NEEDS_LLM (honest deferral): 14,778 tokens (50.0% of vocab,
    35.3% of row-mass).
- **Fuzzy layer false-positive finding:** unguarded fuzzy-ENGLISH mislabeled the
  most critical Hinglish content words (bahut→baht, karna→karma, saath, accha,
  chahiye, kaise, kahan, bahot, salman→salmon — all WRONG labels). Guard applied:
  len ≥ 7, strict distance (1 for ≤9 / 2 for >9), common-English gate (wordfreq
  top-20k). Fuzzy hits dropped 4,151 → 207; residual ~18 Hinglish loanwords
  moved to HINGLISH_OVERRIDE (override grew 31 → 49).
- `reports/wordnet_layer_report.md` written with full findings.
- `requirements.txt`: added `nltk>=3.8` (WordNet corpus).
- `reports/vocab_phinc_freq.tsv` and `reports/wordnet_layer_output.tsv` produced.

## [2026-09-11] FINALIZED Tier 1/2/3 Hinglish normalization architecture + docs carry-forward

- Resolved architecture confirmed and written to
  `reports/hinglish_normalization_architecture.md` (the new single authoritative
  spec). Key decisions recorded:
  - Tier 1 (exact lookup) and Tier 2 (fuzzy edit-distance, penalties 0.1/0.2/1.0,
    R ≥ 0.75) are pure Roman→Roman; **Devanagari is internal-only** and only
    touched by Tier 3 at runtime.
  - Tier 3 = IndicXlit → Devanagari → match a cluster's `canonical_devanagari`
    signature → return `canonical_roman`; no match → log + pass through, never guess.
  - `canonical_map.json` schema: `variants` → cluster id + `clusters` with
    `canonical_roman`, `canonical_devanagari`, `members`, `frequency`;
    provenance sidecar per-token (router verdict, IndicXlit top-4, LLM pick+reason, cluster).
  - Build pipeline order: tokenize+freq → classify w/ override table → IndicXlit
    topk=4 → LLM constrained selection → cluster by Devanagari similarity → pick
    canonicals → emit JSON + sidecar.
- `AGENTS.md` updated: reports tree lists the architecture doc; Next Steps item 0
  is rewritten from the spec, including the two build gates (P1 override table,
  P6 batch-collapse/determinism).
- `PROBLEMS.md`: added **P6** — IndicXlit batch-collapse (36/50 in verification
  test) + determinism must be confirmed at real scale (build gate G2).
- Gemini free tier confirmed usable for the LLM constrained-selection step
  (`gemini-3.5-flash-lite`; strict-JSON output verified 2026-09-11).

## [2026-09-11] Gemini health check — new API key verified working

- `.env` API key swapped; re-ran `scripts/gemini_health_check.py`.
- Plain-text call returned `OK` (15.9s first-call latency), strict-JSON call
  parsed cleanly first try (`{"status": "ok", "model": ...}`).
- Note for the harness: the model self-reported `gemini-1.5-pro` although the
  target was `gemini-3.5-flash-lite` — the model hallucinates its own name. The
  harness must trust its configured model id, never the model's self-report.

## [2026-09-11] Gemini API health-check script (connectivity + format verification)

- Created `scripts/gemini_health_check.py` — standalone check that loads
  `GEMINI_API_KEY` from the project-root `.env` (python-dotenv, with a manual
  fallback parser), prints the installed SDK version, lists flash-lite models
  via the SDK and picks a free-tier target (`gemini-3.5-flash-lite`), then runs
  a timed plain-text call and a strict-JSON call.
- Uses the current `google-genai` SDK (v2.23.0, `from google import genai`);
  the legacy `google-generativeai` is deprecated (EOL Nov 30 2025) and is
  NOT used.
- Error handling is classified, not a bare try/except: bad-key (400/401/403),
  rate-limit (429, reads Retry-After header), network/timeout, and generic
  errors each print a distinct message.
- JSON path reports whether the model's text parsed raw or needed
  markdown-fence/`{...}`-block stripping (real harness will rely on this).
- Added `google-genai>=2.0,<3.0` to `requirements.txt`.
- **Live result (2026-09-11):** SDK 2.23.0, 55 models visible, 6 flash-lite
  candidates; the key currently in `.env` returns
  `403 PERMISSION_DENIED - Your project has been denied access. Please contact
  support.` on generate calls (list works). Connectivity + error classification
  verified; the API key/project needs attention before the harness builds.

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

## [2026-09-05] Pre-Tier-1 token router (src/token_router.py)

- Added `src/token_router.py` (+ `src/__init__.py`): standalone, dependency-free
  router that classifies a single token into `ENGLISH`,
  `NUMERIC_OR_ALPHANUMERIC`, or `CANDIDATE_HINGLISH`. API: `classify_token(token)`
  -> str, `classify_batch(tokens) -> dict`.
- English wordlist = **wordfreq `top_n_list('en', 50000)`** (pure-Python, bundled
  data, installed in `.venv310`); case-insensitive set lookup. Numeric/alnum =
  regex only (`^\d+$`, `^\d+[a-z]+$`, `^\d+[a-z]+\d*$`, plus general digit+letter
  mix), no dictionary.
- Benchmark on 20 test tokens: 0.11 ms for the batch; ~1 µs/token single-call
  (incl. regex fallback path).
- Known misclassifications (expected, flagged in output, not silently resolved):
  - `kr` → ENGLISH (wordfreq has 'kr'; common Hinglish abbreviation for कर)
  - `bal` → ENGLISH (Hinglish बाल/बल vs English abbreviation)
  - `rh` → ENGLISH (English abbreviation; low Hinglish risk)
  - `acct` → ENGLISH correctly at N=50000 (was CANDIDATE_HINGLISH at N=30000)
  - Ambiguous classics: `main`/`to`/`maine` route to ENGLISH despite common
    Hinglish uses — by design; Tier1/2/3 resolves real ambiguity later.
- Not integrated into Tier 1/2/3 pipeline yet (standalone module + test run only).

## [2026-09-05] reports/ directory + token router report + docs sync

- Created `reports/` directory for verification write-ups (per AGENTS.md
  convention). Moved `indicxlit_verification_report.md` from repo root into it.
- Added `reports/token_router_report.md` — full write-up of the pre-Tier-1
  router: design/wordlist rationale, 20-token results table, misclassification
  analysis (`kr`, `bal`, `rh` collisions; `acct` wordlist-size finding), and
  performance numbers (0.11 ms batch, ~1 µs/token).
- Updated `AGENTS.md`: structure tree (reports/, real `src/` with
  `token_router.py`, `.venv310`), reports convention, interpreter notes, and
  re-ordered Next Steps (Tier 1/2/3 pipeline now step 0).
- Added `wordfreq>=3.0` to `requirements.txt` (English wordlist for the router).

## [2026-09-05] Short-token EN/HI collision diagnostic (PHINC vocabulary)

- Added `scripts/token_collision_diagnostic.py` — extracts the 29,579-token
  lowercase vocabulary from `phinc_cleaned_step1to4.csv` (`Sentence_clean`),
  classifies every token with `classify_token()` (read-only on `token_router.py`),
  buckets by length, and prints frequency-sorted random samples of the danger zone.
- Added `reports/token_collision_diagnostic_report.md` (seed=42). Key numbers:
  ENGLISH share by length — len1 46.2%, len2 56.0%, len3 48.5%, len4 34.5%,
  len5 22.8%, len6 21.4%, len7 23.5%, len8+ 17.3%. Danger zone confirmed as
  length <= 4 (2,383 tokens classified ENGLISH), dominated by high-frequency
  Hinglish function words (`thi` 162 rows, `jab` 149, `hue` 78, `band` 63,
  `ni` 61, `ham` 24). Length-5 collision rate halves and the tokens are rare
  proper nouns rather than function words. Recommended next artifact: explicit
  collision override table for Tier-1 wiring (not a router change).
- AGENTS.md: codified "every report must open with a 'Reason this report exists'
  section" as a standing convention for all future reports; added the diagnostic
  script to the structure tree.

## [2026-09-05] HURDLE: short-token EN/HI collisions are concentrated, not uniform

- Exhaustive (unsampled) export of the length<=4 ENGLISH pool
  (`scripts/export_collision_pool.py` -> `reports/collision_len4_en_freq_sorted.tsv`).
  Pool confirmed at **2,383 tokens**; pool total row-occurrences = **62,486**.
  80% of that frequency mass is covered by the **top 205** tokens by frequency;
  95% by the **top 815**. The damage is heavily concentrated in a short high-frequency
  head (e.g. `hai` 3,661 rows, `to` 1,892, `ke` 1,604, `ki` 1,571, `se` 1,328,
  `ka` 1,244, `ho` 1,178, `ko` 1,149, `aur` 1,023, `bhai` 1,023), then a long
  freq=1 tail with negligible retrieval impact.
- **Hurdle status: OPEN.** The data kills the blanket "<=4 chars -> Hinglish"
  length-cutoff idea (it would wrongly deny ENGLISH status to genuine short
  English function words like `the`, `and`, `for` — confirmed present in the
  pool). Chosen fix direction: a small curated override table targeting the
  high-frequency head (~150-250 tokens covers 80%+ of the mass). Two categories:
  (1) unambiguous always-Hinglish collisions (`thi`, `jab`, `hue`, `band`, `ni`,
  `ham`, `bt`, `kr`, `bal`, `rh`, ...) -> hard-override to CANDIDATE_HINGLISH;
  (2) genuinely context-dependent tokens (`main`/`to`/`maine`) — a
  token-in-isolation router cannot resolve these; document as a real limitation.
- A solution note will be appended to this CHANGELOG when the override table is
  built and validated. Full problem detail is tracked in `PROBLEMS.md`.

## [2026-09-05] HURDLE (follow-up): encoding mojibake reaches the classifier

- Noted via diagnostic: `Γ¥ñ∩╕Å` (cp1252-mangled heart emoji) is a 3-char token
  classified ENGLISH. This is a cleaning gap from Steps 1-4, not a router bug.
  Plan: strip non-alphabetic / mojibake garbage tokens at preprocessing before
  classification. Status: OPEN.

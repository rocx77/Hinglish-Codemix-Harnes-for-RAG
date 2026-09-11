# Pre-Tier-1 Token Router Report

**Date:** 2026-09-05 · **Module:** `src/token_router.py` (+ `src/__init__.py`)
**Status:** standalone module + test run — NOT integrated into Tier 1/2/3 pipeline

## Purpose

Decide whether a token should reach the Hinglish-normalization pipeline at all.
`classify_token(token: str) -> str` returns exactly one of:

| Category | Meaning |
|---|---|
| `ENGLISH` | recognized English word (case-insensitive wordlist lookup) |
| `NUMERIC_OR_ALPHANUMERIC` | purely numeric, or unit/code-like digit+letter tokens |
| `CANDIDATE_HINGLISH` | everything else — passed on to Tier 1/2/3 |

Input contract: already-tokenized, punctuation-stripped tokens (punctuation
handling is a separate tokenizer concern).

## Design & Wordlist Choice

- **English wordlist:** `wordfreq` — `top_n_list('en', 50000)` loaded once into a
  `frozenset`. Chose `wordfreq` over NLTK because it's pure-Python with bundled
  data (no corpus download, no C build) and installs cleanly in `.venv310`.
- **Numeric/alphanumeric:** regex only (not enumerable) — `^\d+$`,
  `^\d+[a-z]+$`, `^\d+[a-z]+\d*$`, plus a general digit+letter mixture check
  (catches `24x7`, `10w30`, `5g`, `1kg`, `4050`).
- **Speed target met:** no model inference; one dict lookup + a few regex checks.
- `classify_batch(tokens: list[str]) -> dict[str, str]` for bulk use.

## Results — 20 test tokens

| Token | Category | Note |
|---|---|---|
| laptop, mobile, phone, wifi, server | **ENGLISH** | correct |
| 5g, 1kg, 4050, 24x7 | **NUMERIC_OR_ALPHANUMERIC** | correct |
| bahut, bht, kaha, uske, padega | **CANDIDATE_HINGLISH** | correct |
| mra, ktn | **CANDIDATE_HINGLISH** | correct |
| kr | **ENGLISH** | ⚠ collision |
| rh | **ENGLISH** | ⚠ collision |
| acct | **ENGLISH** | correct (needs wordlist ≥50k) |
| bal | **ENGLISH** | ⚠ collision |

## Misclassifications & Ambiguities (expected — flagged, not silently resolved)

- **`kr` → ENGLISH.** wordfreq lists "kr", but in Hinglish it's a common
  abbreviation for *कर* (do). Likely practical error: `kr` should route to
  CANDIDATE_HINGLISH for normalization.
- **`bal` → ENGLISH.** Hinglish *बाल* (hair) / *बल* (strength) collides with the
  English abbreviation. Genuine ambiguous token.
- **`rh` → ENGLISH.** English abbreviation (rhesus / right-hand); low Hinglish
  risk, but it is a collision.
- **`acct` → ENGLISH (correct at N=50000).** Routed to CANDIDATE_HINGLISH at
  N=30000 — wordlist size matters; 50k was chosen as the sweet spot (does not
  flip `mra`/`ktn`).
- **Classic ambiguity (by design):** `main` (Eng. "main" / Hin. "I"), `to`
  (Eng. "to" / Hin. "that" *तो*), `maine` (Eng. "Maine"/"maine" / Hin. "I did").
  All route to ENGLISH; the router deliberately picks a side and Tier 1/2/3 is
  responsible for resolving true ambiguity.

## Performance

| Benchmark | Time |
|---|---|
| 20-token batch (`classify_batch`) | 0.11 ms total |
| 1000 single calls | ~1.07 ms (~1 µs/token, incl. regex path) |

## Recommendation

- Add an explicit **collision override table** (e.g. `kr`, `bal`) in
  downstream Tier 1/2/3 wiring rather than changing the router itself, to keep
  the router generic.
- Keep `_EN_WORDLIST_SIZE = 50000`; revisit only if Hinglish short-word
  collisions cost more than rare-English recall gains.

**Reproduce:** `.venv310\Scripts\python.exe src\token_router.py`
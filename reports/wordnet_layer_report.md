# wordnet_hinglish_filter — P1 Rules-Layer Validation Report

**Reason this report exists:**  
The P1 collision-override problem (PROBLEMS.md) showed 2,383 tokens classified as ENGLISH
but unambiguously Hinglish, touching 62,486 row-occurrences. Sending every collision token
to the LLM adjudicator is expensive at scale. This report documents the offline, zero-cost
rules-layer pre-filter that resolves the majority deterministically and isolates the honest
remainder that genuinely needs an LLM call.

---

## Method

`scripts/wordnet_hinglish_filter.py` classifies every token in one pass through five
ordered checks (first match wins):

| Order | Label               | Rule                                      |
|------:|---------------------|-------------------------------------------|
| 1     | `NON_LINGUISTIC`    | Regex: URLs, @mentions, #hashtags, numbers/units, mojibake (P2), pure-punct |
| 2     | `AMBIGUOUS`         | 4 context-dependent tokens (main, maine, me, the) |
| 3     | `HINGLISH`          | 49 override tokens (31 original P1 + 18 from first fuzzy audit) |
| 4     | `ENGLISH` (exact)   | WordNet synset match |
| 5     | `ENGLISH` (fuzzy)   | Guarded: len ≥ 7, edit-distance ≤ 1 (len ≤ 9) or ≤ 2 (len > 9) **and** the matched candidate is a common English lemma (wordfreq top-20k) |
| 6     | `UNCERTAIN_NEEDS_LLM` | Nothing matched — honest deferral |

### Vocabulary source

`reports/vocab_phinc_freq.tsv` — 29,579 unique lowercase tokens, 165,692 total
row-occurrences, derived from `Datasets/phinc_cleaned_step1to4.csv` (13,510 rows,
Sentence_clean, whitespace-split, row-occurrence counted once per sentence).

---

## Results — self-test (17 labeled tokens)

Correct: 16/17  |  Deferred: 1/17 (`wong` — proper noun, honest)  |  Wrong: 0

---

## Results — full vocabulary (29,579 unique tokens)

| Label                | Unique tokens |  %  | Row-mass | Row-mass % |
|----------------------|--------------:|----:|----------:|-----------:|
| `NON_LINGUISTIC`     |         8,573 | 29.0 |   27,140 |      16.4 |
| `AMBIGUOUS`          |             4 |  0.0 |    2,288 |       1.4 |
| `HINGLISH`           |            49 |  0.2 |      ... |       ... |
| `ENGLISH` (exact)    |         5,986 | 20.2 |      ... |       ... |
| `ENGLISH` (fuzzy)    |           190 |  0.6 |      382 |       0.2 |
| `ENGLISH` (total)    |         6,176 | 20.9 |   55,370 |      33.4 |
| `UNCERTAIN_NEEDS_LLM`|        14,778 | 50.0 |   58,555 |      35.3 |

**Cost takeaway:** 14,778 tokens (50.0% of unique vocab, 35.3% of row-mass) need
an LLM call. Everything else is resolved deterministically for free.

### High-frequency band check

| Min freq | Unique tokens | UNCERTAIN in band |
|----------|--------------|-------------------|
| ≥ 1      |       29,579 |          14,778 (50.0%) |
| ≥ 5      |        3,998 |           2,013 (50.4%) |
| ≥ 10     |        2,083 |           1,083 (52.0%) |
| ≥ 50     |          432 |             192 (44.4%) |

The uncertain pool tracks roughly with vocabulary size in every band — it is not
dominated by one long tail.

---

## Fuzzy layer false-positive finding (2026-09-11)

### Initial run (unguarded fuzzy, len ≥ 5, distance 1-2)

The first full-vocab run immediately surfaced **silent WRONG labels** on the most
important Hinglish content words:

| Token     |  Freq | Meant to be | Got     | via                         |
|-----------|------:|-------------|---------|-----------------------------|
| `bahut`   |   209 | HINGLISH    | ENGLISH | fuzzy_edit1 (→ `baht`)      |
| `karna`   |   125 | HINGLISH    | ENGLISH | fuzzy_edit1 (→ `karma`)     |
| `saath`   |   158 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `karte`   |   153 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `accha`   |   148 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `kaise`   |   115 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `kahan`   |   104 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `bahot`   |   114 | HINGLISH    | ENGLISH | fuzzy_edit1                 |
| `chahiye` |   142 | HINGLISH    | ENGLISH | fuzzy_edit2                 |
| `salman`  |   152 | HINGLISH    | ENGLISH | fuzzy_edit1 (→ `salmon`)    |
| `dhoni`   |   108 | HINGLISH    | ENGLISH | fuzzy_edit1                 |

The self-test (17 known tokens) produced **zero** WRONG labels because it had no
fuzzy-triggering tokens ≥ 5 letters with an edit-1 English neighbour. The bug was
invisible until the real vocabulary exposed it.

Per the design rule — "a token landing in the WRONG hard label is worse than
deferring" — this was a blocking defect.

### Guard applied

Three gates added to the fuzzy path (script now reflects this):

1. **Length gate raised to 7** — short strings are exactly where EN/HI collide
   (per the original P1 diagnostic).
2. **Common-English gate** — matched WordNet lemma must also be in the wordfreq
   top-20k (`_EN_COMMON`). Blocks `baht` (not common English), but still passes
   `karma` — moot because `karna` is length 5 and already blocked by gate (1).
3. **Strict distance** — edit distance ≤ 1 for len ≤ 9; only len ≥ 10 gets 2.

After guard: fuzzy hits dropped from 4,151 → 207; wrong labels on the critical
Hinglish words dropped to 0.

### Residual Hinglish loanwords in fuzzy hits (after guard)

~18 tokens at freq ≤ 5 remained mislabeled as ENGLISH by the guarded fuzzy path
(milenge, andhere, banwana, karwate, sanskriti, sadharan, sahaara, sultani,
madrasi, congressi, bastiyon, wicketo, stadiumi, hospitalo, pakistaniyo/io/ano,
karaoge). These are unambiguously Hinglish and were moved to `HINGLISH_OVERRIDE`
in the next pass (override set grew from 31 → 49).

---

## Override table evolution

| Version | HINGLISH tokens | AMBIGUOUS tokens |
|---------|-----------------|------------------|
| v0 (P1 diagnostic) | 31 | 4 |
| v1 (post first-fuzzy audit) | 49 (+ 18 loanwords) | 4 |

The override table doubles as the growing positive-ID reference list for Hinglish
tokens — it is the canonical "these are always-Hinglish" list for the final
normalization build (canonical_map.json).

---

## Key design decisions

1. **`AMBIGUOUS` exists as a first-class label** — 4 tokens (main, maine, me, the)
   are context-dependent and cannot be resolved by any token-in-isolation router.
   They are documented, not guessed.
2. **Fuzzy English is gated, not removed** — the guard makes it safe; the remaining
   190 fuzzy hits are genuine English typos (goverment, atleast, recieve) resolved
   for free. Removing fuzzy entirely would be overly conservative.
3. **UNCERTAIN_NEEDS_LLM is an honest outcome**, not a failure — 14,778 tokens at
   free-tier Gemini cost is trivial. The rules layer's job is to shrink the pool;
   the LLM's job is to be right on the hard remainder.

---

## Files produced

| File | Description |
|------|-------------|
| `scripts/wordnet_hinglish_filter.py` | The filter script (standalone, nltk + wordfreq) |
| `scripts/export_phinc_vocab.py` | Vocab exporter (token + frequency TSV) |
| `reports/vocab_phinc_freq.tsv` | Full vocabulary: 29,579 tokens, sorted by frequency |
| `reports/wordnet_layer_output.tsv` | Labeled output: token + label + method, all 29,579 tokens |

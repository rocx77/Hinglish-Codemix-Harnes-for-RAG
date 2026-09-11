# Short-Token Exact-Match Audit — English/Hinglish collision in the WordNet exact layer

**Reason this report exists:** The fuzzy-layer fix
(`reports/wordnet_layer_report.md`) closed one instance of the P1 collision bug
class, but a review of that work flagged that the **exact WordNet match (step 4)
runs unconditionally on every token — including 2-4 letter tokens, exactly the
danger zone P1 identified.** A real English dictionary entry sitting on or near a
common Hinglish word silently lands in `ENGLISH (exact)` and bypasses
normalization, corrupting the ground truth the `canonical_map.json` build will
consume. This report records the audit that tests that hypothesis against the
shipped `reports/wordnet_layer_output.tsv`, so the decision to promote tokens to
`HINGLISH_OVERRIDE` is backed by evidence rather than the current "only fixed
when discovered" posture.

---

## The argument being tested

Order of operations in `scripts/wordnet_hinglish_filter.py`:

```
regex prefilter -> AMBIGUOUS override -> HINGLISH override -> WordNet EXACT -> WordNet fuzzy (guarded) -> UNCERTAIN
```

The fuzzy layer only produces a label after the length gate (>= 7) and the
common-English gate. **The exact layer has neither.** It fires on the first
Hinglish token that happens to also be a valid WordNet entry. Today that is
masked for a handful of known cases (`band`, `ham`, `bal`, `rh`...) only because
they sit in the 49-token `HINGLISH_OVERRIDE` set, which is checked *before*
WordNet and wins by ordering. That is a patch for known cases, not a structural
fix: any short, common Hinglish token that is a valid WordNet entry and is not
yet in the override list will be confidently mislabeled `ENGLISH (exact)` with
zero warning — the same silent-WRONG failure mode the fuzzy audit surfaced, just
as-yet-unexposed in a different layer.

---

## Method

1. Load `reports/wordnet_layer_output.tsv` (token, label, method) and
   `reports/vocab_phinc_freq.tsv` (token, rows_containing_token) with
   `pd.read_csv(..., sep="\t", quoting=3)` (QUOTE_NONE — tokens contain `"`).
2. Keep only `label == "ENGLISH"` AND `method == "wordnet_exact"`.
3. Filter `len(token) <= 4` and `len(token) == 5`; sort by row-mass descending.
4. Eyeball the frequency head (this report: top 80 for <= 4, top 60 for == 5).

## Results

| Bucket | Tokens | Row-mass |
|--------|-------:|---------:|
| exact ENGLISH, len <= 4 | 1,589 | 24,641 |
| exact ENGLISH, len == 5 | 2,610 | 30,315 |

### Confirmed hypothesis — live WRONG labels in the shipped output

The following tokens carry `ENGLISH\twordnet_exact` **in the current
`reports/wordnet_layer_output.tsv`** yet are unambiguously Hinglish in this
corpus. Verified by direct line match, not inferred from the table:

| Token | Row-mass | Meaning | English collision |
|-------|---------:|---------|-------------------|
| `par` | 404 | par (on/at) | golf "par" |
| `ji`  | 364 | ji (honorific) | (Devanagari-sense match) |
| `pe`  | 355 | pe (on, postposition) | (rare "pe") |
| `k`   | 347 | ka (of) truncated | (letter k) |
| `aa`  | 309 | aa/aan (come) | (interjection) |
| `hum` | 271 | ham (we/us) | (letter-name hm?) |
| `tum` | 256 | tum (you) | (dim. join, rare) |
| `h`   | 252 | hai (is) truncated | (letter h) |
| `mere`| 232 | mere (my/mine) | adjective "mere" |
| `din` | 230 | din (day) | noise "din" |
| `log` | 230 | log (people) | noun/log learner "log" |
| `de`  | 229 | de (give) | (letter de) |
| `bas` | 229 | bas (enough/only) | (base/bass senses) |
| `le`  | 219 | le (take) | (French-influenced lemma) |
| `mat` | 180 | mat (don't / prohibition) | floor "mat" |
| `hua` | 167 | hua (happened) | (rare) |
| `wale`| 166 | waale (postposition) | (suffix lemma) |
| `lag` | 127 | lag (feel/apply) | "lag" |
| `agar`| 119 | agar (if) | (agar jelly) |
| `mil` |  97 | mil (meet) | "mil" (length unit) |
| `fir` |  77 | phir (then) | "fir" (tree) |
| `bola`|  75 | bola (said) | (rare) |
| `tera`|  72 | tera (your) | (rare) |
| `hone`|  69 | hone (to be, oblique) | (hone) |
| `beta`|  60 | beta (son) | "beta" |

Sum of confirmed row-mass: **~5,100 row-occurrences across 25 tokens**. These
are the same magnitude of error the fuzzy audit caught (`bahut` 209, `saath`
158, ...) — the exact layer just happens to have a *larger* latent pool because
it has no gate at all.

Adjacent but context-sensitive (need review, not auto-override): `hi` (994, likely
mostly English greeting but also hai truncation), `khan` (72, surname), `logo`
(85, English "logo" vs Hindi log-og-plural), `ha` (61, English "ha!" vs haan),
`jo`/`b`/`u` (single letters), plus honest English function words that must stay
(`is`, `in`, `the`, `at`, `it`, `on`, `so`, `are`, `but`, `or`, `like`, `was`,
`will`, `all`, `up`, `not`, `good`, `no`, `have`, ...).

The len==5 head is mostly genuine (india, match, tweet, delhi, happy, party,
trump, phone, movie, world...) with a small Hinglish spill: `paise` (111),
`sakti` (34), `saale` (26), `beech` (24), `khaya` (21), `milne` (20). Lower
density — a per-token review, not a mass fix.

---

## Structural root cause

WordNet's vocabulary legitimately contains short entries whose spellings
coincide with the most common Hinglish function words. The exact layer has no
durational guard because the fix must NOT be a blanket length gate: that would
wrongly defer genuinely-English short words (`is`, `the`, `at`, `it`, ...) —
the same false-positive trap P1 already recorded as a "dead end avoided." The
correct mechanism is **curation, structurally enforced**: the `HINGLISH_OVERRIDE`
set is the ONLY safe home for known short Hinglish tokens, and an audited
top-frequency sweep must be part of validating any future vocabulary rerun, the
same way the built-in self-test is.

---

## The four review recommendations — disposition

1. **Short-token exact-match audit** — DONE (this report). Result: hypothesis
   confirmed; 25 live WRONG labels (~5,100 rows). **Before the LLM adjudication
   pass starts, promote the 25 confirmed always-Hinglish tokens to
   `HINGLISH_OVERRIDE` and regenerate `wordnet_layer_output.tsv`.**
2. **Grow the validation set** — PENDING. n=17 cannot support an accuracy claim.
   Plan: stratified hand-labeled sample — 50 short tokens, 50 mid-length,
   50 fuzzy-triggering, 50 random UNCERTAIN — to report real precision/recall
   per class. This is a required measurement for any report that calls the
   rules layer "trustworthy."
3. **Quoting fix** — CLARIFIED. The two pipeline scripts are *already* safe:
   `export_phinc_vocab.py` writes and `wordnet_hinglish_filter.py` reads via
   plain `open()` + `split("\t")`, never the pandas CSV parser, so the `"`
   tokens cannot shift columns in the pipeline itself. The `quoting=3`
   (QUOTE_NONE) requirement applies ONLY to downstream pandas consumers of the
   TSVs (e.g. analysis/audit scripts). Enforced here and in the audit.
4. **Confidence-check LLM pass on resolved buckets** — DEFERRED (nice-to-have).
   A 100-200 token spot-check of ENGLISH-exact and HINGLISH-override through the
   LLM would yield an empirical error bound for the rules layer instead of an
   assumed one. Not blocking; improves report rigor if budget permits.

---

## Decision gate

- **Blocker:** promote the 25 audited tokens to `HINGLISH_OVERRIDE` +
  regenerate + re-audit (the 8-10 context-sensitive ones stay in review).
- **Required for "rules layer is calibrated":** the stratified validation set
  (point 2).
- **Optional:** confidence-check LLM pass (point 4).

Tracked as PROBLEMS.md P8.
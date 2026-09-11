# Hinglish Normalization Pipeline — Resolved Tier 1/2/3 Architecture

## Reason this report exists

This is the **finalized architecture** for the Hinglish normalization pipeline
(Tier 1/2/3), decided on 2026-09-11. It exists so any future agent or reader
implements the pipeline from a single authoritative spec rather than from
stale notes or half-forgotten conversation. It records the *resolved* design
decisions (notably: Devanagari is internal-only, and only Tier 3 touches it at
runtime), the `canonical_map.json` schema, the build pipeline in exact order,
and the open dependency gates that must close before the build can run. If a
future reader only reads one file about normalization, this is it.

---

## 1. Runtime behavior: three tiers (Devanagari is internal-only)

The pipeline normalizes Roman-script (Latin) Hinglish tokens to a **canonical
Roman spelling**. Devanagari is strictly an *internal matching key* — it is
never part of the output and never leaks into the benchmark corpus.

```
tier0: router (src/token_router.py) + collision-override table
         └── only CANDIDATE_HINGLISH proceeds
tier1: exact lookup   variant → cluster_id → canonical_roman     (Roman→Roman)
tier2: fuzzy edit-distance vs known Roman variant keys            (Roman→Roman)
tier3: neural fallback — IndicXlit → Devanagari → cluster signature (Roman→Deva→Roman)
```

- **Tier 0 (routing):** `src/token_router.classify_token()` classifies each
  token as `ENGLISH` / `NUMERIC_OR_ALPHANUMERIC` / `CANDIDATE_HINGLISH`. The
  **collision-override table** (PROBLEMS.md P1) is merged *in here* — it
  overrides the short-token EN/HI collision head (`hai`, `kr`, `bal`, `rh`,
  `thi`, `jab`, ...) to `CANDIDATE_HINGLISH`. This table is a **dependency that
  is still open**; the build must not run on the full vocabulary until it is
  built and validated. Only `CANDIDATE_HINGLISH` tokens proceed to Tier 1/2/3.
- **Tier 1 (exact lookup):** `variant → cluster_id → canonical_roman`.
  Pure Roman-to-Roman, no Devanagari involved. This resolves the dictionary
  head (`bht → bahut`, `bohot → bahut`).
- **Tier 2 (fuzzy edit-distance):** Compares the incoming Roman token directly
  against known Roman variant keys using the **weighted penalty table**:
  - phonetic swap: **0.1**
  - vowel modification: **0.2**
  - consonant swap: **1.0**
  - acceptance threshold: **R ≥ 0.75**
  Still no Devanagari here. Reuses the same cost matrix/formula as the
  near-duplicate-translation grouping used in Step 4 cleaning.
- **Tier 3 (neural fallback):** Reached **only on a genuine Tier 1+2 miss**.
  1. IndicXlit the novel token to Devanagari (`en → hi`, `topk=4`).
  2. Compare that Devanagari against each cluster's stored **canonical
     Devanagari signature** (not the Roman form) to find which existing cluster
     it phonetically belongs to.
  3. If matched, return that cluster's `canonical_roman`.
  4. If nothing is close enough → it is a genuinely unmapped word: **log it and
     pass it through unchanged. Never guess.**

### Why this shape

- Roman-to-Roman tiers stay deterministic and ~µs-fast for the corpus head.
- Devanagari membership is a *better* phonetic anchor than Roman edit distance
  for novel spellings (e.g. `kya` vs `kia`) because it is the actual script
  that the speaker intends — this is exactly where the neural step earns its
  keep at **runtime**, not only at build time.
- Tier 3's "log and pass through, never guess" rule prevents silent
  corruption of the corpus.

---

## 2. Data schema — `canonical_map.json`

Every cluster stores **two** artifacts, not one: the output key and the
internal matching key.

```json
{
  "variants": {
    "bahut": "c001",
    "bht": "c001",
    "bohot": "c001"
  },
  "clusters": {
    "c001": {
      "canonical_roman": "bahut",
      "canonical_devanagari": "बहुत",
      "members": ["bahut", "bht", "bohot", "bahoot"],
      "frequency": 214
    }
  }
}
```

- `variants`: every known Roman spelling → cluster id. **This is Tier 1's
  lookup table.**
- `clusters[cXXX].canonical_roman`: the actual output spelling (**Tier 1/2/3
  all return this**).
- `clusters[cXXX].canonical_devanagari`: the internal matching signature
  (**only Tier 3 uses it**).
- `clusters[cXXX].members`: all Roman variants merged into this cluster.
- `clusters[cXXX].frequency`: aggregate corpus frequency (for tie-breaking and
  provenance).

**Provenance / debug sidecar** (`canonical_map_provenance.json`, proposed name):
per-token `{router verdict, IndicXlit raw top-4, LLM pick + reasoning, final
cluster}`. Kept for the paper's methodology appendix and for auditing the build.

**Output locations (proposed; finalize at implementation):**
`Datasets/canonical_map.json` + `Datasets/canonical_map_provenance.json`,
alongside the cleaned corpus.

---

## 3. Build pipeline (in order)

1. **Tokenize** cleaned PHINC vocabulary; get per-token corpus frequency.
2. **Classify** every unique token via `token_router.classify_token` **with the
   collision-override table merged in**.
   ⚠️ GATE: the override table (P1) is still unbuilt — this step is blocked
   until it is constructed and validated.
   Only `CANDIDATE_HINGLISH` tokens survive.
3. **IndicXlit** (`en → hi`, `topk=4`) on every surviving token.
   ⚠️ GATE: confirm the **batch-collapse** and **determinism** issues from the
   earlier verification are resolved before this first real-scale run.
   Known from `reports/indicxlit_verification_report.md` / PROBLEMS.md P6:
   `batch_transliterate_words` collapses repeated identical inputs in
   `post_process` (50 inputs / 9 unique → 36 outputs) — feed distinct words,
   and verify outputs are identical run-to-run (determinism).
4. **LLM constrained selection:** given the token + example sentence(s) +
   IndicXlit's 4 candidates, pick the best candidate (or "none usable").
   Planned on the Gemini free tier (`gemini-3.5-flash-lite`), connectivity now
   verified by `scripts/gemini_health_check.py`. The harness must trust its
   **configured model id, never the model's self-reported name** (the model
   hallucinates its own model string — observed 2026-09-11).
5. **Cluster** tokens by phonetic similarity of their **chosen Devanagari
   outputs**, reusing the Tier 2 cost matrix / R ≥ 0.75 threshold as an offline
   dedup pass (same technique as the near-duplicate-translation grouping).
6. **Per cluster:** `canonical_roman` = highest-frequency Roman variant in the
   cluster; `canonical_devanagari` = that same variant's selected Devanagari.
7. **Emit** `canonical_map.json` + the provenance sidecar.

---

## 4. Open dependency gates (must close before full build)

| # | Gate | Where tracked | Who owns closing it |
|---|------|---------------|---------------------|
| G1 | Collision-override table built, validated, and merged into Tier-0 classification | PROBLEMS.md P1 | Normalization build (Step 2) |
| G2 | IndicXlit batch-collapse workaround + determinism confirmed at scale | PROBLEMS.md P6, `reports/indicxlit_verification_report.md` | Normalization build (Step 3) |
| G3 | LLM constrained-selection cost/format on Gemini free tier (JSON output verified working; latency ~10-16 s first-call) | `scripts/gemini_health_check.py` | Normalization build (Step 4) |

---

## 5. Related artifacts

- `src/token_router.py` — Tier 0 router (`classify_token` / `classify_batch`,
  wordfreq `top_n_list('en', 50000)`).
- `reports/token_collision_diagnostic_report.md` + `collision_len4_en_freq_sorted.tsv`
  — the P1 collision data (80% of mass in top 205 tokens; 95% in top 815).
- `reports/indicxlit_verification_report.md` — IndicXlit env fixes + latency
  (7.07 ms/word batched, CPU) + batch caveats.
- `scripts/gemini_health_check.py` — Gemini connectivity/format verification.
- PROBLEMS.md P1, P2 (mojibake pre-process drop — applies before router), P6.
# PROBLEMS.md — Problems Encountered & Solutions Found

**Purpose:** A running, detailed log of the problems we hit while building this
project and how we resolved (or plan to resolve) each one. Kept deliberately
verbose — this is the "lessons learned" file. Short lifecycle notes go in
`CHANGELOG.md`; this file is the full story. Each open problem carries a clear
status so a future agent knows what is still pending.

Format per problem: **Status** · **First seen** · **Symptom** · **Root cause** ·
**Why it mattered** · **Solution** (found or planned).

---

## P1 — Short-token English/Hinglish collisions (length ≤ 4)

- **Status:** OPEN (hurdle)
- **First seen:** 2026-09-05 (pre-Tier-1 token router diagnostics)
- **Symptom:** `classify_token()` routes many Hinglish short tokens to ENGLISH.
  In the cleaned 13,510-row PHINC corpus, the length ≤ 4 pool contains 2,383
  unique tokens classified ENGLISH, touching **62,486 row-occurrences**. The
  highest-frequency offenders are unmistakably Hinglish: `hai` (3,661 rows),
  `to` (1,892 = तो), `ke` (1,604 = के), `ki` (1,571 = कि/की), `se` (1,328 = से),
  `ka` (1,244 = का), `ho` (1,178), `ko` (1,149), `aur` (1,023), `bhai` (1,023),
  `kar`, `kya`, `ek`, `toh`, `ab`, `koi`, `na`, `aap`, `ne`, `tha`, `main`, `tu`.
- **Root cause:** Hinglish function words (2-4 Latin letters) collide with the
  English wordfreq list used by the router. Short tokens are exactly where the
  two vocabularies overlap.
- **Why it mattered:** ENGLISH-classified tokens bypass the Tier-1/2/3 Hinglish
  normalization (roman → Devanagari). Every collision silently skips
  normalization of a real Hinglish word, corrupting the normalized corpus that
  feeds the RAG search benchmark. Left alone, this biases retrieval metrics.
- **Critical measurement (the turning point):** The damage is NOT uniform.
  Cumulative coverage (exhaustive export, `reports/collision_len4_en_freq_sorted.tsv`):
  **80% of the frequency mass is covered by the top 205 tokens; 95% by the top
  815.** This makes the fix tractable: review ~150-250 tokens, not 2,383.
- **Dead end avoided (learned from data):** A blanket "length ≤ 4 → force
  Hinglish/HINGLISH" rule was considered and rejected **because the same pool
  contains genuine short English function words** (`the` 848, `is` 544, `and`
  384 `in` 447, `of` 352, ...). A length gate fixes false negatives by creating
  a new pile of false positives. This is exactly why we measured before fixing.
- **Solution (planned, not yet built):** A small curated **override table**
  targeting the high-frequency head, consumed by the Tier-1 normalization wiring
  (NOT hardcoded into `src/token_router.py`). Two categories surfaced by the data:
  1. **Unambiguous always-Hinglish** (`thi`, `jab`, `hue`, `band`, `ni`, `ham`,
     `bt`, `kr`, `bal`, `rh`, `hai`, `to`, `ke`, ...) → hard-override to
     CANDIDATE_HINGLISH unconditionally.
  2. **Context-dependent ambiguous** (`main`/`to`/`maine`, `me`, `the`) → a
     token-in-isolation router CANNOT resolve these correctly. Document this as a
     real, stated limitation in the write-up rather than papering over it.
- **Validation plan:** After building the table, re-run the two diagnostics to
  confirm English-share-per-length drops for the Hinglish words while genuine
  English tokens stay ENGLISH, and log the numbers.
- **Progress (2026-09-11 — P1 rules-layer BUILD + VALIDATED):** The P1
  zero-cost pre-filter `scripts/wordnet_hinglish_filter.py` was built, validated
  on a 17-token self-test (16 correct / 1 deferred / 0 wrong), and run on the
  full vocabulary. It resolves one bucket deterministically before any LLM call:
  NON_LINGUISTIC 8,573 · AMBIGUOUS 4 · HINGLISH 49 (override) · ENGLISH 6,176
  (5,986 exact + 190 guarded-fuzzy) · **UNCERTAIN_NEEDS_LLM 14,778** (50.0% of
  vocab, 35.3% of row-mass). Full numbers and the fuzzy-guard finding in
  `reports/wordnet_layer_report.md`; labeled output in
  `reports/wordnet_layer_output.tsv`. The final override table for the
  Tier-1 wiring still ships the high-frequency head, but now rides on this
  validated classification instead of the raw collision pool.

---

## P2 — Encoding mojibake reaches the classifier (emoji garbage)

- **Status:** SOLVED (2026-09-11)
- **First seen:** 2026-09-05 (collision diagnostic sample)
- **Symptom:** `Γ¥ñ∩╕Å` (a heart emoji mangled through a cp1252-ish decode) is a
  3-char token classified ENGLISH in the danger-zone sample. Similar mojibake
  artifacts (`ΓÇª` ellipsis, `Γ¼ç∩╕Å`) appear in the corpus.
- **Root cause:** The downstream cleaning steps replaced/left some non-ASCII
  characters that were decoded to garbage; the cleaning pipeline (Steps 1-4)
  operates on characters somewhere else in the chain, and no step strips
  non-alphabetic tokens before classification.
- **Why it mattered:** Mojibake tokens pollute the vocabulary and would be
  shipped through normalization/benchmarking; they are also exactly the kind of
  token that makes a downstream evaluator's accuracy numbers look wrong.
- **Solution (found — P1 rules-layer pre-filter, 2026-09-11):** The regex
  prefilter in `scripts/wordnet_hinglish_filter.py` now drops tokens containing
  characters outside a sane set (`[a-zA-Z\u0900-\u097F]`) as NON_LINGUISTIC
  BEFORE any classifier sees them. Mojibake (`Γ¥ñ∩╕Å`) fails that check and never
  reaches the router. Kept in the preprocessing/rules layer, NOT in
  `token_router.py`.
- **Note:** Distinct from P1 — this is a cleaning gap, not a routing logic issue.

---

## P3 — fairseq cannot build on Windows (no MSVC toolchain)

- **Status:** SOLVED
- **First seen:** 2026-09-05 (IndicXlit env setup)
- **Symptom:** `pip install ai4bharat-transliteration` died compiling fairseq's
  C extensions: `building 'fairseq.libbleu' extension -> Microsoft Visual C++
  14.0 or greater is required`.
- **Root cause:** (a) fairseq 0.12.2 ships Cython/C++ extensions
  (`libbleu`, `data_utils_fast`, `token_block_utils_fast`, `libbase`, `libnat`);
  (b) the installed VS 2022 Build Tools at
  `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools` is a partial
  stub — `VC\Tools\MSVC\14.44.35207` has only `Auxiliary/`, `include/`,
  `modules/` (no `bin/`), and there is no Windows Kits SDK
  (`C:\Program Files (x86)\Windows Kits\10\Include` missing). So no C/C++
  toolchain actually exists on this machine.
- **Why it mattered:** `ai4bharat-transliteration` (IndicXlit) depends on
  fairseq; without it the whole roman→Devanagari Hinglish normalization depends
  on a third-party cloud API instead of a local model.
- **Solution (found):** None of the C extensions are needed for *inference*.
  fairseq imports them lazily inside training/scoring code paths. So:
  1. Downloaded the fairseq 0.12.2 sdist and edited its `setup.py` to set
     `extensions = []` and `cmdclass = {}` (kill all C/Cython builds).
  2. `pip install`ed the patched sdist into a Python 3.10 venv (`.venv310`) —
     pure-Python install, succeeds with no compiler.
  3. One module is still imported by the IndicXlit inference path:
     `fairseq.data.data_utils_fast`. Wrote a pure-Python `data_utils_fast.py`
     transcribed 1:1 from the `.pyx`, implementing `batch_by_size_fn`,
     `batch_by_size_vec`, `batch_fixed_shapes_fast` (np.split semantics).
- **Gotcha reminders:** Any future fairseq upgrade re-installs the broken
  C-extension build; keep the patched sdist and shim noted. MSVC toolchain on
  this machine is unusable — do not plan on compiling anything locally.

---

## P4 — Python version trap: fairseq can't build / run on 3.13

- **Status:** SOLVED
- **First seen:** 2026-09-05 (IndicXlit env setup)
- **Symptom:** On Python 3.13, `pip install ai4bharat-transliteration` failed
  with `FileNotFoundError: fairseq\version.txt` during fairseq's
  `write_version_py`; also fairseq's own docs warn it predates 3.11.
- **Root cause:** fairseq 0.12.2 is pinned to older Python (3.8-3.10 era) and
  its Cython/setuptools dance is incompatible with 3.11+.
- **Why it mattered:** The project `.venv` was Python 3.13.13 — IndicXlit could
  not run there at all.
- **Solution (found):** Installed a dedicated **Python 3.10.11** (`winget
  install Python.Python.3.10`) and created a dedicated venv `.venv310` for all
  IndicXlit/token-router work. The general cleaning pipeline keeps using the
  default `.venv` (3.13). Interpreter split is documented in `AGENTS.md`.

---

## P5 — PyTorch 2.6+ `weights_only=True` rejects the IndicXlit checkpoint

- **Status:** SOLVED
- **First seen:** 2026-09-05 (IndicXlit model load)
- **Symptom:** `XlitEngine(lang2use="hi")` init failed with
  `_pickle.UnpicklingError: Weights only load failed ... GLOBAL
  argparse.Namespace was not an allowed global by default`.
- **Root cause:** PyTorch ≥ 2.6 changed the default of `torch.load(...)` from
  `weights_only=False` to `weights_only=True`. The official AI4Bharat v1.0
  checkpoint pickles an `argparse.Namespace` (and other objects) that the safe
  loader rejects.
- **Why it mattered:** The loader is deep inside fairseq
  (`checkpoint_utils.load_checkpoint_to_cpu`); the stock package was unusable
  with modern torch.
- **Solution (found):** Patched the installed
  `.venv310\Lib\site-packages\fairseq\checkpoint_utils.py` to pass
  `weights_only=False` at both `torch.load` sites. The checkpoint comes from the
  official AI4Bharat release (trusted source), so accepting full unpickling is
  safe here. (Alternative rejected: add_safe_globals — the checkpoint contains
  many custom classes; weights_only=False is the intended path for a trusted
  checkpoint.)

---

## P6 — IndicXlit at scale: batch-collapse + determinism must be confirmed before the real build

- **Status:** OPEN (verification gate)
- **First seen:** 2026-09-05 (verification), flagged as a build-blocking gate on
  2026-09-11 (resolved architecture)
- **Symptom:** The native batch API `batch_transliterate_words` collapses
  repeated identical inputs in `post_process` — the 50-word test (9 unique) came
  back with 36 candidate sets. The extended test also showed the model needs
  deterministic outputs (same input run-to-run) before it can be trusted to map
  the whole PHINC vocabulary in one pass.
- **Root cause:** Known library behaviour (a `FIXME` in
  `base_engine.py:batch_transliterate_words`); not yet exercised at real scale
  (unique tokens, `topk=4`) or checked for run-to-run determinism on this
  machine.
- **Why it mattered:** The Tier 1/2/3 build (Step 3) is the **first time
  IndicXlit runs at real scale** rather than on 9 smoke-test words. If batch
  collapse or nondeterminism leaks in, the LLM constrained-selection pass and
  the clustering step both silently work from corrupted candidates.
- **Solution (planned):** Before the full build: (1) confirm all vocab tokens
  fed per batch call are distinct (batch-collapse workaround); (2) run a
  fixed subset of unique tokens twice and diff the `topk` candidates for
  equality; (3) log the numbers in this file and the verification report.
- **Carried in:** `reports/hinglish_normalization_architecture.md`
  (gate G2) and `reports/indicxlit_verification_report.md`.

---

## P7 — Fuzzy-ENGLISH layer silently mislabeled Hinglish content words at scale

- **Status:** SOLVED (2026-09-11)
- **First seen:** 2026-09-11 (first full-vocab run of the P1 rules pre-filter)
- **Symptom:** Unguarded fuzzy matching (len ≥ 5, edit distance 1-2) produced
  silent WRONG `ENGLISH` labels on the most important Hinglish content words:
  `bahut` (209, via `baht`), `saath` (158), `karte` (153), `salman` (152, via
  `salmon`), `accha` (148), `chahiye` (142, edit-2), `karna` (125, via `karma`),
  `kaise` (115), `bahot` (114), `kahan` (104), `dhoni` (108). Frequencies 104-209
  — the opposite of a long tail.
- **Root cause:** WordNet's fuzzy neighbourhood is full of valid English words
  that are edit-distance 1-2 from common Hinglish; short tokens (5-6 letters)
  are exactly where EN/HI collide (P1). Self-testing in the script (17 known
  tokens) produced 0 wrong labels because none of the samples had a
  fuzzy-triggering form — the bug was invisible until real vocabulary ran.
- **Why it mattered:** A hard `ENGLISH` label is used to short-circuit
  normalization. Every wrong label silently skips Hinglish normalization for a
  high-frequency content word. Per the design rule — "a token landing in the
  WRONG hard label is worse than deferring" — this was a blocking defect.
- **Solution (found):** Three gates on the fuzzy path:
  1. **Length gate** raised to 7 (short strings = collision zone).
  2. **Common-English gate** — matched WordNet lemma must be in wordfreq top-20k
     (`_EN_COMMON`; blocks `baht`, passes `karma`, moot since `karna` is len 5).
  3. **Strict distance** — ≤ 1 for len ≤ 9, only len ≥ 10 gets 2.
  Result: fuzzy hits dropped 4,151 → 207; zero wrong labels on the critical
  words (all now UNCERTAIN_NEEDS_LLM). ~18 residual Hinglish loanwords (freq ≤ 5:
  milenge, andhere, banwana, karwate, sanskriti, sadharan, sahaara, sultani,
  madrasi, congressi, bastiyon, wicketo, stadiumi, hospitalo, pakistaniyo/io/ano,
  karaoge) were moved to HINGLISH_OVERRIDE (31 → 49).
- **Lesson:** Fuzzy layers must be trained-sensitive, not just self-test-clean.
  The self-test passing with the layer broken is the failure mode to guard
  against — keep the audit-of-high-frequency-mislabel checks in
  `reports/wordnet_layer_report.md` in mind for any future fuzzy layer.
- **Full story:** `reports/wordnet_layer_report.md` (§ Fuzzy layer
  false-positive finding).

---

## P8 — WordNet EXACT match has no length gate (same bug class as P1/P7)

- **Status:** OPEN (audit done, fix under review)
- **First seen:** 2026-09-11 (review of the P1 rules-layer validation)
- **Symptom:** The exact WordNet check (`wordnet_exact`, step 4) runs on every
  token with no length gate. Tokens like `par` (404), `ji` (364), `pe` (355),
  `hum` (271), `tum` (256), `mere` (232), `din` (230), `log` (230), `mat`
  (180), `hua` (167), `wale` (166), `agar` (119) — all unambiguous Hinglish in
  this corpus — carry `ENGLISH\twordnet_exact` in the CURRENT shipped
  `reports/wordnet_layer_output.tsv`. Audit found **25 live WRONG labels**,
  ~5,100 row-occurrences total.
- **Root cause:** Same root as P1/P7. WordNet legitimately contains short
  English entries whose spellings coincide with the most common Hinglish
  function words. The exact layer has no gate at all, so the only thing
  stopping mislabeling today is the 49-token `HINGLISH_OVERRIDE` set being
  checked BEFORE WordNet — a patch for known cases, not a structural fix.
- **Why it mattered:** A hard `ENGLISH` label bypasses Hinglish normalization.
  Any short Hinglish token that is also a valid WordNet entry and not yet in
  the override set is silently routed ENGLISH with zero warning — the exact
  failure mode P7 documents for the fuzzy layer, larger because there is no
  gate whatsoever.
- **Solution (planned):** Do NOT add a blanket length gate — it would wrongly
  defer genuine English short words (`is`, `the`, `at`, `it`, ...) per the P1
  documented dead-end. Instead: (1) promote the 25 audited always-Hinglish
  tokens to `HINGLISH_OVERRIDE` and regenerate; (2) treat a freq-sorted
  short-token audit as a required validation step on every future vocab rerun;
  (3) resolve the adjacent context-sensitive list (`hi`, `khan`, `logo`, `ha`)
  on a per-token basis.
- **Carried in:** `reports/exact_match_short_token_audit.md` (full method,
  evidence tables, decision gate).

---

## P9 — WordNet filter classified the input vocabulary's header row as a token

- **Status:** SOLVED (2026-09-11)
- **First seen:** 2026-09-11 (Task 0 of the canonical-map build)
- **Symptom:** `reports/wordnet_layer_output.tsv` had 29,580 data rows instead
  of the documented 29,579. Line 2 of the file was `token\tENGLISH\twordnet_exact`.
- **Root cause:** `run_on_vocab_file` (scripts/wordnet_hinglish_filter.py) fed
  EVERY input line of `vocab_phinc_freq.tsv` to the classifier, including the
  vocabulary file's own header row (`token\trows_containing_token`). `token` is
  a valid WordNet word, so it became a spurious ENGLISH entry.
- **Why it mattered:** One fake token per build would silently enter the
  canonical map and any downstream join, with zero error message. Also a
  general class of bug ("did not skip the header") any agent could repeat on a
  new vocabulary file.
- **Solution (found):** Header detection + skip in `run_on_vocab_file`: first
  field is case-insensitively `token` AND the second field is not an integer ->
  treat as header, log, continue. Regenerated output: 29,579 rows; ENGLISH
  6,176 -> 6,175; all other buckets unchanged. Note: one-column vocab files
  whose first token is literally `token` will be skipped as a header — the skip
  is always logged so this edge is visible.

---

## P10 — Pandas default-parse of the TSVs silently misparses quote-containing tokens

- **Status:** GUARDRAIL (mitigated, not fixable in-pipeline)
- **First seen:** 2026-09-11 (documented in the exact-match audit, re-measured
  in Task 0)
- **Symptom:** `pd.read_csv("reports/vocab_phinc_freq.tsv", sep="\t")` returns
  26,541 rows; `wordnet_layer_output.tsv` returns 26,542 — ~3,000 rows
  silently shifted/merged, zero error. Tokens containing `"` (532 of them,
  e.g. `hai"`, `"ye`, `"bhai`) were misparsed as quoted fields.
- **Root cause:** pandas default CSV writer/parser treats `"` as a quote
  character (RFC4180). Our TSVs are written by plain `open()` writes that never
  quote, so a literal `"` inside a token collides with the parser's quoting.
- **Why it mattered:** Column shifts are silent — downstream joins and sums
  produce plausible-looking wrong numbers (the exact hazard the batch-collapse
  P6 describes for IndicXlit).
- **Solution (mitigation):** The two pipeline scripts are SAFE — they use
  `open()` + `split("\t")`, never the pandas parser. Any downstream pandas
  consumer MUST pass `quoting=csv.QUOTE_NONE, keep_default_na=False`. The
  canonical-map build reads these files exclusively via `QUOTE_NONE` (Task 0
  fixed/deliverable files). A future switch to pandas-native reads would
  reintroduce this.

---

_Append new problems at the end. When a problem is solved, flip its Status to
SOLVED and describe what worked — that "how we overcame it" note is the whole
point of this file._
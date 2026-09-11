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
- **Where the data lives:** `reports/token_collision_diagnostic_report.md`
  (sampled view), `reports/collision_len4_en_freq_sorted.tsv` (exhaustive
  2,383-row table, token+length+frequency, sorted).

---

## P2 — Encoding mojibake reaches the classifier (emoji garbage)

- **Status:** OPEN (follow-up)
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
- **Solution (planned):** A preprocessing pass that drops tokens containing
  characters outside a sane set (latin letters / digits, and later Devanagari),
  BEFORE the router sees them. This belongs in the cleaning/preprocessing layer,
  NOT in `token_router.py`.
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

_Append new problems at the end. When a problem is solved, flip its Status to
SOLVED and describe what worked — that "how we overcame it" note is the whole
point of this file._
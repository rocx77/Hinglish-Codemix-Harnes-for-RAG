# AGENTS.md — Project Conventions & Future Work Guide

## Project Overview

**HinglishCodeMix Harness for RAG** — a research project for experimenting with
Retrieval-Augmented Generation (RAG) on Hinglish/English code-mixed data.

The main workflow:
1. Clean the raw PHINC parallel corpus
2. Build a search benchmark from the cleaned data
3. Run retrieval (BM25, dense) and reranking experiments
4. Evaluate and analyse results

---

## Project Structure

```
HinglishCodeMix_Harness for RAG/
│
├── AGENTS.md                  # You are here — agent instructions
├── CHANGELOG.md               # Log of all changes (append-only)
├── PROBLEMS.md                # Detailed problems-encountered & solutions log
├── README.md                  # Project overview
├── requirements.txt           # Python dependencies
├── .gitignore
│
├── Datasets/                  # Raw + cleaned data
│   ├── English-Hindi code-mixed parallel corpus.csv   (raw, do not edit)
│   └── phinc_cleaned_step1to4.csv                     (generated output)
│
├── scripts/                   # Executable pipeline scripts (numbered order)
│   ├── clean_phinc.py         # Steps 1-4: load, clean, dedup PHINC
│   ├── verify_indicxlit.py    # IndicXlit verification (API + smoke + latency)
│   ├── token_collision_diagnostic.py  # Short-token EN/HI collision diagnostics
│   ├── export_collision_pool.py       # Exhaustive freq-sorted len<=4 EN pool export
│   ├── export_phinc_vocab.py          # Full vocab + row-freq export (canonical-map step 1)
│   ├── wordnet_hinglish_filter.py     # P1 zero-cost rules pre-filter (nltk WordNet + wordfreq gate)
│   ├── task1_pilot_pool.py            # Canonical-map Task 1: UNCERTAIN pilot pool by coverage tier
│   ├── task2_batch_integrity.py       # Canonical-map Task 2: IndicXlit batch-integrity gate (.venv310)
│   ├── task3_adjudicate_pilot.py      # Canonical-map Task 3: per-token Gemini adjudication (resume-safe)
│   ├── task4_candidate_pool.py        # Canonical-map Task 4: merge overrides + adjudicated, Deva top-4 (.venv310)
│   ├── task5_build_canonical_map.py   # Canonical-map Task 5: emit canonical_map.json (candidate_1 = final)
│   ├── 02_build_benchmark.py  # (planned) Build benchmark from cleaned data
│   ├── 03_run_retrieval.py    # (planned) Run BM25 / dense retrieval
│   ├── 04_rerank.py           # (planned) Reranking experiments
│   ├── 05_evaluate.py         # (planned) Metrics and evaluation
│   └── 06_failure_analysis.py # (planned) Error analysis
│
├── src/                       # Reusable library modules
│   ├── token_router.py        # Pre-Tier-1 router (ENGLISH / numeric / Hinglish)
│   ├── data/                  # (planned) Data loading and preprocessing
│   ├── retrieval/             # (planned) BM25, dense retriever implementations
│   ├── reranking/             # (planned) Cross-encoder, LLM rerankers
│   ├── evaluation/            # (planned) Metrics (MRR, MAP, NDCG, etc.)
│   └── analysis/              # (planned) Failure analysis utilities
│
├── reports/                   # Reports and verification write-ups
│   ├── hinglish_normalization_architecture.md  # FINALIZED Tier 1/2/3 design (read first)
│   ├── token_router_report.md
│   ├── indicxlit_verification_report.md
│   ├── token_collision_diagnostic_report.md
│   ├── wordnet_layer_report.md         # P1 rules-layer validation (fuzzy-guard finding)
│   ├── exact_match_short_token_audit.md # Short-token exact-ENGLISH collision audit (P8, pre-canonical-map)
│   └── collision_len4_en_freq_sorted.tsv   (full 2,383-token override-table source data)
│
├── tests/                     # (planned) Unit tests
│
├── code-mixed-search-benchmark/   # Git-ignored local subproject (keep as-is)
│
└── .venv/ .venv310/               # Virtual environments (gitignored)
```

---

## Conventions

### File & Folder Rules

- **Raw data is read-only.** Never modify files in `Datasets/` that start with
  `English-Hindi`. Only the script output (`phinc_cleaned_*.csv`) may change.
- **Scripts go in `scripts/`** and are numbered `01_`, `02_`, etc. to show
  execution order. Name them `<number>_<descriptive_name>.py`.
- **Reusable code goes in `src/`** as importable modules, not scripts.
- **Tests go in `tests/`** and mirror the module they test (`test_data.py`,
  `test_retrieval.py`, etc.).
- **Reports and verification write-ups go in `reports/`** as Markdown.
- **Every report must open with a "Reason this report exists" section** stating
  why it was generated (what decision it informs, what it guards against), so
  any future reader/agent understands the report's purpose without guessing.

### Code Style

- Python 3.11+, type hints encouraged but not required for quick scripts.
- Use `pandas` for tabular data. Avoid excessive chaining; keep transformations
  readable.
- Use `os.path.join(ROOT, ...)` for paths, where `ROOT` is derived from the
  script's location — never hardcode absolute Windows paths.
- Keep console output ASCII-safe (Windows cp1252 terminal). Use the UTF-8
  wrapper pattern at the top of scripts if needed:
  ```python
  import sys, io
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
  ```

### Running Scripts

Always run scripts from the **project root**:
```bash
python scripts/clean_phinc.py
```

Interpreter notes: the general pipeline uses the default `python` (`src/`,
`scripts/clean_phinc.py`). IndicXlit + token-router work (requires `wordfreq`,
`ai4bharat-transliteration`) runs under **`.venv310\Scripts\python.exe`**
(Python 3.10.11 — fairseq cannot build on 3.13).

### Logging Changes

Every time you make a change, append a dated entry to `CHANGELOG.md`. Follow
the format:
```markdown
## [YYYY-MM-DD] Short title

- What changed and why.
- Any numbers / metrics worth noting.
```

---

## Pipeline Status

| Step | Script                  | Status      | Output                              |
|------|-------------------------|-------------|-------------------------------------|
| 1    | `scripts/clean_phinc.py`| **Done**    | `Datasets/phinc_cleaned_step1to4.csv` |
| 2    | Build benchmark         | Not started | —                                   |
| 3    | Run retrieval           | Not started | —                                   |
| 4    | Reranking               | Not started | —                                   |
| 5    | Evaluate                | Not started | —                                   |
| 6    | Failure analysis        | Not started | —                                   |

---

## Next Steps (when resuming work)

0. **Normalization architecture is FINALIZED — read
   `reports/hinglish_normalization_architecture.md` first.** It is the single
   authoritative spec for the Tier 1/2/3 pipeline:
   - **Tier 0** = `src/token_router.py` + the P1 collision-override table
     (still unbuilt — opening the vocabulary build without it is a blocker).
   - **Tier 1** exact lookup and **Tier 2** fuzzy edit-distance are pure
     Roman→Roman; Tier 2 uses the weighted penalty table (phonetic swap 0.1,
     vowel mod 0.2, consonant swap 1.0), threshold R ≥ 0.75.
   - **Tier 3** neural fallback (only on a genuine Tier 1+2 miss) is the only
     step that touches Devanagari at runtime: IndicXlit → Devanagari → match
     against a cluster's `canonical_devanagari` signature → return that cluster's
     `canonical_roman`. No match → log and pass through unchanged, never guess.
   - **Devanagari is internal-only** and never emitted; `canonical_map.json`
     stores both `canonical_roman` (output) and `canonical_devanagari`
     (internal signature) per cluster, plus `variants` → cluster id, `members`,
     `frequency`; a provenance sidecar documents router/IndicXlit/LLM decisions.
   - **Build pipeline (in order):** tokenize+freq → classify w/ override table →
     IndicXlit topk=4 (GATE: batch-collapse & determinism — P6) → LLM
     constrained selection (Gemini free tier, verified by
     `scripts/gemini_health_check.py`; trust the configured model id, not the
     model's self-report) → cluster by Devanagari similarity reusing the Tier 2
     matrix → pick canonicals (highest-frequency variant) → emit JSON + sidecar.
1. **Noisy-data handling & N-selection** — review `translation_too_short` flag
   and `near_dup_group_id` clusters to decide what to keep/drop for benchmarking.
2. **Step 2: Build benchmark** — generate query/passage pairs from the cleaned
   corpus; produce a benchmark JSONL for retrieval evaluation.
3. **Step 3: Retrieval** — implement BM25 and dense retrievers, index the
   benchmark, retrieve top-k results.
4. **Steps 4-6** — reranking, metrics, failure analysis.

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
│   ├── 02_build_benchmark.py  # (planned) Build benchmark from cleaned data
│   ├── 03_run_retrieval.py    # (planned) Run BM25 / dense retrieval
│   ├── 04_rerank.py           # (planned) Reranking experiments
│   ├── 05_evaluate.py         # (planned) Metrics and evaluation
│   └── 06_failure_analysis.py # (planned) Error analysis
│
├── src/                       # (planned) Reusable library modules
│   ├── data/                  #   Data loading and preprocessing
│   ├── retrieval/             #   BM25, dense retriever implementations
│   ├── reranking/             #   Cross-encoder, LLM rerankers
│   ├── evaluation/            #   Metrics (MRR, MAP, NDCG, etc.)
│   └── analysis/              #   Failure analysis utilities
│
├── tests/                     # (planned) Unit tests
│
├── code-mixed-search-benchmark/   # Existing subproject (keep as-is)
│
└── .venv/                         # Virtual environment (gitignored)
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

1. **Noisy-data handling & N-selection** — review `translation_too_short` flag
   and `near_dup_group_id` clusters to decide what to keep/drop for benchmarking.
2. **Step 2: Build benchmark** — generate query/passage pairs from the cleaned
   corpus; produce a benchmark JSONL for retrieval evaluation.
3. **Step 3: Retrieval** — implement BM25 and dense retrievers, index the
   benchmark, retrieve top-k results.
4. **Steps 4-6** — reranking, metrics, failure analysis.

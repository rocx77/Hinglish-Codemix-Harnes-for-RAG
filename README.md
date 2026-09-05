# HinglishCodeMix Harness for RAG

Experimenting with Retrieval-Augmented Generation (RAG) on Hinglish/English
code-mixed data using the PHINC parallel corpus.

## Project Structure

```
Datasets/                          Raw + cleaned data
  English-Hindi ... corpus.csv     Raw PHINC (read-only)
  phinc_cleaned_step1to4.csv       Cleaned output

scripts/                           Pipeline scripts (run in order)
  clean_phinc.py                   Step 1-4: load, clean, dedup
  (02-06 planned)

AGENTS.md                          Agent instructions & conventions
CHANGELOG.md                       Change log (append-only)
```

## Setup

```bash
pip install -r requirements.txt
python scripts/clean_phinc.py
```

## Pipeline

| Step | Script           | Description                       | Status |
|------|------------------|-----------------------------------|--------|
| 1    | `clean_phinc.py` | Clean PHINC corpus (Steps 1-4)    | Done   |
| 2    | Build benchmark  | Generate query/passage pairs       | TODO   |
| 3    | Run retrieval    | BM25 + dense retrieval             | TODO   |
| 4    | Rerank           | Cross-encoder / LLM reranking      | TODO   |
| 5    | Evaluate         | MRR, MAP, NDCG metrics             | TODO   |
| 6    | Failure analysis | Error pattern analysis             | TODO   |

See `AGENTS.md` for conventions and `CHANGELOG.md` for progress.
